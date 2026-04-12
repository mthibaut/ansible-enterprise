#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import os
import pathlib
import sys

from proxmox_infra_render import (
    build_infra_config,
    env_bool,
    env_int,
    help_epilog,
    parser_kwargs,
    render_yaml_document,
    SUPPORTED_PROVIDERS,
)


def parse_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(
                f"line {line_no}: expected exactly 2 whitespace-separated columns: "
                "hostname artifact"
            )
        rows.append((parts[0], parts[1]))
    return rows


def increment_ip(ip_start_cidr: str, offset: int) -> str:
    iface = ipaddress.ip_interface(ip_start_cidr)
    network = iface.network
    new_ip = iface.ip + offset
    if new_ip not in network:
        raise ValueError(f"incremented IP {new_ip} falls outside network {network}")
    return f"{new_ip}/{network.prefixlen}"


def render_hosts_ini(
    rows: list[tuple[str, str]],
    *,
    ansible_user: str,
    ip_start_cidr: str,
    ansible_group: str = "all",
    ansible_port: int | None = None,
    ansible_connection: str | None = None,
    ansible_become: bool | None = None,
    ansible_become_method: str | None = None,
) -> str:
    lines = [f"[{ansible_group}]"]
    for offset, (hostname, _artifact) in enumerate(rows):
        host_ip = str(ipaddress.ip_interface(increment_ip(ip_start_cidr, offset)).ip)
        parts = [f"{hostname} ansible_host={host_ip} ansible_user={ansible_user}"]
        if ansible_port is not None:
            parts.append(f"ansible_port={ansible_port}")
        if ansible_connection is not None:
            parts.append(f"ansible_connection={ansible_connection}")
        if ansible_become is not None:
            parts.append(f"ansible_become={'true' if ansible_become else 'false'}")
        if ansible_become_method is not None:
            parts.append(f"ansible_become_method={ansible_become_method}")
        lines.append(" ".join(parts))
    return "\n".join(lines) + "\n"


def write_inventory(
    *,
    rows: list[tuple[str, str]],
    out_dir: pathlib.Path,
    provider: str,
    instance_type: str,
    id_start: int,
    ip_start_cidr: str,
    gateway: str | None,
    bridge: str,
    state: str,
    rebuild_on: str,
    ansible_user: str,
    ansible_group: str,
    ansible_port: int | None,
    ansible_connection: str | None,
    ansible_become: bool | None,
    ansible_become_method: str | None,
    node: str | None,
    storage: str | None,
    artifact_storage: str,
    cores: int | None,
    memory: int | None,
    disk: str | None,
    nameserver: str | None,
    searchdomain: str | None,
    onboot: bool | None,
    started: bool | None,
    unprivileged: bool | None,
    force: bool,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    host_vars_dir = out_dir / "host_vars"
    host_vars_dir.mkdir(parents=True, exist_ok=True)

    hosts_ini = out_dir / "hosts.ini"
    if hosts_ini.exists() and not force:
        raise FileExistsError(f"{hosts_ini} already exists; pass --force to overwrite")
    hosts_ini.write_text(
        render_hosts_ini(
            rows,
            ansible_user=ansible_user,
            ip_start_cidr=ip_start_cidr,
            ansible_group=ansible_group,
            ansible_port=ansible_port,
            ansible_connection=ansible_connection,
            ansible_become=ansible_become,
            ansible_become_method=ansible_become_method,
        ),
        encoding="utf-8",
    )

    for offset, (hostname, artifact) in enumerate(rows):
        host_dir = host_vars_dir / hostname
        host_dir.mkdir(parents=True, exist_ok=True)
        infra_yml = host_dir / "infra.yml"
        if infra_yml.exists() and not force:
            raise FileExistsError(f"{infra_yml} already exists; pass --force to overwrite")
        config = build_infra_config(
            provider=provider,
            instance_type=instance_type,
            instance_id=id_start + offset,
            artifact=artifact,
            ip_cidr=increment_ip(ip_start_cidr, offset),
            gateway=gateway,
            bridge=bridge,
            state=state,
            rebuild_on=rebuild_on,
            node=node,
            storage=storage,
            artifact_storage=artifact_storage,
            cores=cores,
            memory=memory,
            disk=disk,
            nameserver=nameserver,
            searchdomain=searchdomain,
            onboot=onboot,
            started=started,
            unprivileged=unprivileged,
        )
        infra_yml.write_text(render_yaml_document(config), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create hosts.ini and host_vars/<host>/infra.yml from 2-column Proxmox input.",
        epilog=help_epilog("ID_START", "IP_START", "OUT_DIR", "ANSIBLE_USER"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--provider", default=os.environ.get("PROXMOX_PROVIDER", "proxmox"))
    parser.add_argument("--type", choices=["lxc", "vm"], dest="instance_type", **parser_kwargs(suffix="TYPE", required=True))
    parser.add_argument("--id-start", type=int, default=env_int("ID_START"), required=env_int("ID_START") is None)
    parser.add_argument("--ip-start", help="Starting IP/CIDR, incremented once per row", **parser_kwargs(suffix="IP_START", required=True))
    parser.add_argument("--out-dir", **parser_kwargs(suffix="OUT_DIR", default="inventory-scaffold"))
    parser.add_argument("--gateway", **parser_kwargs(suffix="GATEWAY"))
    parser.add_argument("--bridge", **parser_kwargs(suffix="BRIDGE", default="vmbr0"))
    parser.add_argument("--state", choices=["present", "absent"], **parser_kwargs(suffix="STATE", default="present"))
    parser.add_argument("--rebuild-on", choices=["never", "config_change", "always"], **parser_kwargs(suffix="REBUILD_ON", default="never"))
    parser.add_argument("--ansible-user", **parser_kwargs(suffix="ANSIBLE_USER", default="root"))
    parser.add_argument("--ansible-group", **parser_kwargs(suffix="ANSIBLE_GROUP", default="all"))
    parser.add_argument("--ansible-port", type=int, default=env_int("ANSIBLE_PORT"))
    parser.add_argument("--ansible-connection", **parser_kwargs(suffix="ANSIBLE_CONNECTION"))
    parser.add_argument("--ansible-become", action=argparse.BooleanOptionalAction, default=env_bool("ANSIBLE_BECOME"))
    parser.add_argument("--ansible-become-method", **parser_kwargs(suffix="ANSIBLE_BECOME_METHOD"))
    parser.add_argument("--node", **parser_kwargs(suffix="NODE"))
    parser.add_argument("--storage", **parser_kwargs(suffix="STORAGE"))
    parser.add_argument("--artifact-storage", **parser_kwargs(suffix="ARTIFACT_STORAGE", default="local:vztmpl"))
    parser.add_argument("--cores", type=int, default=env_int("CORES"))
    parser.add_argument("--memory", type=int, default=env_int("MEMORY"))
    parser.add_argument("--disk", **parser_kwargs(suffix="DISK"))
    parser.add_argument("--nameserver", **parser_kwargs(suffix="NAMESERVER"))
    parser.add_argument("--searchdomain", **parser_kwargs(suffix="SEARCHDOMAIN"))
    parser.add_argument("--onboot", action=argparse.BooleanOptionalAction, default=env_bool("ONBOOT"))
    parser.add_argument("--started", action=argparse.BooleanOptionalAction, default=env_bool("STARTED"))
    parser.add_argument("--unprivileged", action=argparse.BooleanOptionalAction, default=env_bool("UNPRIVILEGED"))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"unsupported provider '{args.provider}'; supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )
    rows = parse_rows(sys.stdin.read())
    write_inventory(
        rows=rows,
        out_dir=pathlib.Path(args.out_dir),
        provider=args.provider,
        instance_type=args.instance_type,
        id_start=args.id_start,
        ip_start_cidr=args.ip_start,
        gateway=args.gateway,
        bridge=args.bridge,
        state=args.state,
        rebuild_on=args.rebuild_on,
        ansible_user=args.ansible_user,
        ansible_group=args.ansible_group,
        ansible_port=args.ansible_port,
        ansible_connection=args.ansible_connection,
        ansible_become=args.ansible_become,
        ansible_become_method=args.ansible_become_method,
        node=args.node,
        storage=args.storage,
        artifact_storage=args.artifact_storage,
        cores=args.cores,
        memory=args.memory,
        disk=args.disk,
        nameserver=args.nameserver,
        searchdomain=args.searchdomain,
        onboot=args.onboot,
        started=args.started,
        unprivileged=args.unprivileged,
        force=args.force,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
