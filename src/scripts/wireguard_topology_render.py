#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import subprocess
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import yaml


def wg(*args: str, stdin: str | None = None) -> str:
    result = subprocess.run(
        ["wg", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def gen_keypair() -> tuple[str, str]:
    private_key = wg("genkey")
    public_key = wg("pubkey", stdin=private_key + "\n")
    return private_key, public_key


def gen_psk() -> str:
    return wg("genpsk")


def san(name: str) -> str:
    return name.replace("-", "_")


def pair_key(a: str, b: str) -> frozenset[str]:
    return frozenset({a, b})


def participants(network: dict) -> list[str]:
    net_type = network["type"]
    if net_type == "mesh":
        return list(network["members"])
    if net_type == "hub":
        return [network["hub"], *list(network.get("clients", []))]
    raise ValueError(f"unknown network type: {net_type}")


def host_address(network: dict, host: str, topology: dict) -> str:
    subnet = ipaddress.ip_network(network["subnet"])
    if network["type"] == "mesh":
        idx = network["members"].index(host)
        return str(subnet.network_address + 1 + idx)
    if host == network["hub"]:
        return str(subnet.network_address + 1)
    octet = topology["clients"][host]["octet"]
    return str(subnet.network_address + octet)


def prefix_len(network: dict) -> int:
    return ipaddress.ip_network(network["subnet"]).prefixlen


def endpoint_with_port(topology: dict, host: str, port: int) -> str:
    endpoint = topology["hosts"][host]["endpoint"]
    return endpoint if ":" in endpoint else f"{endpoint}:{port}"


@dataclass
class State:
    priv: dict[tuple[str, str], str] = field(default_factory=dict)
    pub: dict[tuple[str, str], str] = field(default_factory=dict)
    psk: dict[tuple[str, frozenset[str]], str] = field(default_factory=dict)

    def drop_network(self, network_name: str) -> None:
        self.priv = {k: v for k, v in self.priv.items() if k[1] != network_name}
        self.pub = {k: v for k, v in self.pub.items() if k[1] != network_name}
        self.psk = {k: v for k, v in self.psk.items() if k[0] != network_name}


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def all_hosts(topology: dict) -> set[str]:
    hosts: set[str] = set()
    for network in topology["networks"].values():
        hosts.update(participants(network))
    return hosts


def load_state(root: Path, topology: dict) -> State:
    state = State()

    for host in all_hosts(topology):
        public_doc = load_yaml(root / "host_vars" / host / "wireguard.yml")
        for network_name, public_key in (public_doc.get("wireguard_public_keys") or {}).items():
            state.pub[(host, network_name)] = str(public_key)

        for network_name, network in topology["networks"].items():
            vault_doc = load_yaml(root / "host_vars" / host / f"wireguard_vault_{network_name}.yml")
            private_var = f"vault_wireguard_{san(network_name)}_private_key"
            if private_var in vault_doc:
                state.priv[(host, network_name)] = str(vault_doc[private_var])
            psk_prefix = f"vault_wg_psk_{san(network_name)}_"
            for var_name, value in vault_doc.items():
                if not var_name.startswith(psk_prefix):
                    continue
                peer_san = var_name[len(psk_prefix):]
                for other in participants(network):
                    if other != host and san(other) == peer_san:
                        state.psk[(network_name, pair_key(host, other))] = str(value)
                        break

    return state


def generate_missing(state: State, topology: dict) -> None:
    for network_name, network in topology["networks"].items():
        for host in participants(network):
            if (host, network_name) not in state.priv:
                private_key, public_key = gen_keypair()
                state.priv[(host, network_name)] = private_key
                state.pub[(host, network_name)] = public_key
            elif (host, network_name) not in state.pub:
                state.pub[(host, network_name)] = wg(
                    "pubkey", stdin=state.priv[(host, network_name)] + "\n"
                )

        for a, b in combinations(participants(network), 2):
            key = (network_name, pair_key(a, b))
            if key not in state.psk:
                state.psk[key] = gen_psk()


def peer_list_for(host: str, network_name: str, network: dict, topology: dict, state: State) -> list[dict]:
    peers: list[dict] = []
    net_type = network["type"]
    for other in participants(network):
        if other == host:
            continue
        if net_type == "hub" and host != network["hub"] and other != network["hub"]:
            continue

        peer: dict = {
            "name": other,
            "public_key": state.pub[(other, network_name)],
            "preshared_key": "{{ vault_wg_psk_" + san(network_name) + "_" + san(other) + " }}",
        }

        if net_type == "mesh":
            allowed = [f"{host_address(network, other, topology)}/{prefix_len(network)}"]
            allowed += list((network.get("member_routes") or {}).get(other, []))
            peer["allowed_ips"] = allowed
            peer["endpoint"] = endpoint_with_port(topology, other, network["port"])
            peer["persistent_keepalive"] = 25
        elif host == network["hub"]:
            peer["allowed_ips"] = [f"{host_address(network, other, topology)}/32"]
        else:
            if network.get("default_route"):
                peer["allowed_ips"] = ["0.0.0.0/0", "::/0"]
            else:
                allowed = [f"{host_address(network, network['hub'], topology)}/32"]
                allowed += list(network.get("extra_routes", []))
                peer["allowed_ips"] = allowed
            peer["endpoint"] = endpoint_with_port(topology, other, network["port"])
            peer["persistent_keepalive"] = 25

        peers.append(peer)
    return peers


def build_host_doc(host: str, topology: dict, state: State) -> dict:
    public_keys: dict[str, str] = {}
    instances: list[dict] = []

    for network_name, network in topology["networks"].items():
        if host not in participants(network):
            continue

        public_keys[network_name] = state.pub[(host, network_name)]
        address = f"{host_address(network, host, topology)}/{prefix_len(network)}"
        is_client = network["type"] == "hub" and host != network["hub"]

        instance: dict = {
            "name": f"wg-{network_name}",
            "address": [address],
            "private_key": "{{ vault_wireguard_" + san(network_name) + "_private_key }}",
            "peers": peer_list_for(host, network_name, network, topology, state),
        }
        if not is_client:
            instance["listen_port"] = network["port"]
        if is_client and network.get("default_route") and network.get("dns"):
            instance["dns"] = list(network["dns"])
        instances.append(instance)

    return {
        "wireguard_public_keys": public_keys,
        "wireguard_instances": instances,
    }


def build_vault_doc(host: str, network_name: str, network: dict, state: State) -> dict:
    doc: dict[str, str] = {
        f"vault_wireguard_{san(network_name)}_private_key": state.priv[(host, network_name)],
    }
    for other in participants(network):
        if other == host:
            continue
        doc[f"vault_wg_psk_{san(network_name)}_{san(other)}"] = state.psk[
            (network_name, pair_key(host, other))
        ]
    return doc


def render_wg_conf(host: str, network_name: str, network: dict, topology: dict, state: State) -> str:
    lines = [
        f"# wg-{network_name} on {host} - generated by wireguard_topology_render.py",
        "# DO NOT EDIT; regenerate from topology",
        "",
        "[Interface]",
        f"PrivateKey = {state.priv[(host, network_name)]}",
        f"Address = {host_address(network, host, topology)}/{prefix_len(network)}",
    ]

    is_client = network["type"] == "hub" and host != network["hub"]
    if not is_client:
        lines.append(f"ListenPort = {network['port']}")
    if is_client and network.get("default_route") and network.get("dns"):
        lines.append(f"DNS = {', '.join(network['dns'])}")

    net_type = network["type"]
    for other in participants(network):
        if other == host:
            continue
        if net_type == "hub" and host != network["hub"] and other != network["hub"]:
            continue

        lines.extend(
            [
                "",
                f"# {other}",
                "[Peer]",
                f"PublicKey = {state.pub[(other, network_name)]}",
                f"PresharedKey = {state.psk[(network_name, pair_key(host, other))]}",
            ]
        )

        if net_type == "mesh":
            allowed = [f"{host_address(network, other, topology)}/{prefix_len(network)}"]
            allowed += list((network.get("member_routes") or {}).get(other, []))
            lines.append(f"AllowedIPs = {', '.join(allowed)}")
            lines.append(f"Endpoint = {endpoint_with_port(topology, other, network['port'])}")
            lines.append("PersistentKeepalive = 25")
        elif host == network["hub"]:
            lines.append(f"AllowedIPs = {host_address(network, other, topology)}/32")
        else:
            if network.get("default_route"):
                lines.append("AllowedIPs = 0.0.0.0/0, ::/0")
            else:
                allowed = [f"{host_address(network, network['hub'], topology)}/32"]
                allowed += list(network.get("extra_routes", []))
                lines.append(f"AllowedIPs = {', '.join(allowed)}")
            lines.append(f"Endpoint = {endpoint_with_port(topology, other, network['port'])}")
            lines.append("PersistentKeepalive = 25")

    return "\n".join(lines) + "\n"


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_conf(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a WireGuard topology YAML into host_vars and wg-quick configs.",
    )
    parser.add_argument(
        "-i",
        "--inventory",
        required=True,
        help="Inventory root containing host_vars/",
    )
    parser.add_argument(
        "-t",
        "--topology",
        required=True,
        help="Topology YAML file describing hosts, clients, and networks",
    )
    parser.add_argument(
        "--conf-dir",
        default="wg-conf",
        help="Output directory under the inventory root for ready-to-use wg-quick configs",
    )
    parser.add_argument(
        "--rotate",
        action="append",
        default=[],
        help="Network name to force-rotate key material for; repeatable",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    topology = load_yaml(Path(args.topology))
    inventory_root = Path(args.inventory)
    state = load_state(inventory_root, topology)

    for network_name in args.rotate:
        if network_name not in topology.get("networks", {}):
            raise SystemExit(f"unknown network in --rotate: {network_name}")
        state.drop_network(network_name)

    generate_missing(state, topology)

    hosts = all_hosts(topology)
    conf_root = inventory_root / args.conf_dir
    for host in sorted(hosts):
        write_yaml(
            inventory_root / "host_vars" / host / "wireguard.yml",
            build_host_doc(host, topology, state),
        )
        for network_name, network in topology["networks"].items():
            if host not in participants(network):
                continue
            write_yaml(
                inventory_root / "host_vars" / host / f"wireguard_vault_{network_name}.yml",
                build_vault_doc(host, network_name, network, state),
            )
            write_conf(
                conf_root / host / f"wg-{network_name}.conf",
                render_wg_conf(host, network_name, network, topology, state),
            )

    print(
        f"wrote configs for {len(hosts)} hosts across {len(topology['networks'])} networks"
        + (f"; rotated: {', '.join(args.rotate)}" if args.rotate else "")
    )
    print(f"ready-to-use wg-quick confs: {conf_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
