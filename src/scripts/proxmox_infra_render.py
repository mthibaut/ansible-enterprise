#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import os
import sys

import yaml


ENV_PREFIX = "PROXMOX_"
SUPPORTED_PROVIDERS = {"proxmox"}
COMMON_ENV_SUFFIXES = [
    "PROVIDER",
    "TYPE",
    "STATE",
    "REBUILD_ON",
    "NODE",
    "GATEWAY",
    "BRIDGE",
    "STORAGE",
    "ARTIFACT_STORAGE",
    "CORES",
    "MEMORY",
    "DISK",
    "NAMESERVER",
    "SEARCHDOMAIN",
    "ONBOOT",
    "STARTED",
    "UNPRIVILEGED",
]
ENV_DESCRIPTIONS = {
    "PROVIDER": "Infra provider name. Currently only 'proxmox' is supported.",
    "TYPE": "Instance type: 'lxc' or 'vm'.",
    "STATE": "Desired lifecycle state: 'present' or 'absent'.",
    "REBUILD_ON": "Rebuild policy: 'never', 'config_change', or 'always'.",
    "NODE": "Target Proxmox node name.",
    "GATEWAY": "Default gateway IP for the primary network.",
    "BRIDGE": "Proxmox bridge for the primary network, such as vmbr0.",
    "STORAGE": "Primary Proxmox storage target for disks/rootfs.",
    "ARTIFACT_STORAGE": "Storage prefix for LXC template filenames that do not already include one. This must point to a file-based Proxmox storage with Container template content.",
    "CORES": "vCPU count override.",
    "MEMORY": "Memory override in MB.",
    "DISK": "LXC root disk value such as local:8.",
    "NAMESERVER": "Guest resolver IP address.",
    "SEARCHDOMAIN": "Guest resolver search domain.",
    "ONBOOT": "Whether the guest should start automatically with the host.",
    "STARTED": "Whether the guest should be running after provisioning.",
    "UNPRIVILEGED": "Whether to create an unprivileged LXC.",
    "ID": "Guest numeric ID for the single rendered infra block.",
    "ARTIFACT": "LXC template artifact or VM template name.",
    "IP": "Primary guest IP/CIDR, such as 192.0.2.10/24.",
    "ID_START": "Starting numeric ID for scaffolded hosts; increments by one per row.",
    "IP_START": "Starting guest IP/CIDR for scaffolded hosts; increments by one per row.",
    "OUT_DIR": "Output directory for generated hosts.ini and host_vars/ content.",
    "ANSIBLE_USER": "ansible_user value written into hosts.ini.",
}


def env_name(suffix: str) -> str:
    return ENV_PREFIX + suffix


def env_string(suffix: str) -> str | None:
    value = os.environ.get(env_name(suffix))
    if value is None:
        return None
    value = value.strip()
    return value or None


def env_int(suffix: str) -> int | None:
    value = env_string(suffix)
    if value is None:
        return None
    return int(value)


def env_bool(suffix: str) -> bool | None:
    value = env_string(suffix)
    if value is None:
        return None
    normalized = value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{env_name(suffix)} must be a boolean value")


def parser_kwargs(*, suffix: str, default=None, required: bool = False) -> dict:
    env_default = os.environ.get(env_name(suffix))
    kwargs = {"default": env_default if env_default is not None else default}
    if required and env_default is None:
        kwargs["required"] = True
    return kwargs


def env_help_lines(*extra_suffixes: str) -> list[str]:
    suffixes = list(COMMON_ENV_SUFFIXES) + list(extra_suffixes)
    return [
        f"  {env_name(suffix):<28} {ENV_DESCRIPTIONS[suffix]}"
        for suffix in suffixes
    ]


def help_epilog(*extra_suffixes: str) -> str:
    lines = [
        "Environment variable defaults:",
        "  CLI flags override environment variables.",
        "  Supported provider: proxmox",
        "",
        "Common variables:",
        *env_help_lines(*extra_suffixes),
        "",
        "Boolean variables accept: 1/0, true/false, yes/no, on/off",
    ]
    return "\n".join(lines)


def _normalize_ip(ip_cidr: str) -> str:
    ipaddress.ip_interface(ip_cidr)
    return ip_cidr


def _strip_cidr(ip_cidr: str) -> str:
    return str(ipaddress.ip_interface(ip_cidr).ip)


def _normalize_lxc_artifact_storage(artifact_storage: str) -> str:
    storage = artifact_storage.strip().rstrip("/")
    if not storage:
        raise ValueError("artifact_storage must not be empty")
    if ":" not in storage:
        return f"{storage}:vztmpl"
    return storage


def build_infra_config(
    *,
    provider: str = "proxmox",
    instance_type: str,
    instance_id: int,
    artifact: str,
    ip_cidr: str,
    gateway: str | None = None,
    bridge: str = "vmbr0",
    state: str = "present",
    rebuild_on: str = "never",
    node: str | None = None,
    storage: str | None = None,
    artifact_storage: str = "local:vztmpl",
    cores: int | None = None,
    memory: int | None = None,
    disk: str | None = None,
    nameserver: str | None = None,
    searchdomain: str | None = None,
    onboot: bool | None = None,
    started: bool | None = None,
    unprivileged: bool | None = None,
) -> dict:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"unsupported provider '{provider}'; supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )
    if instance_type not in {"lxc", "vm"}:
        raise ValueError("type must be 'lxc' or 'vm'")
    if state not in {"present", "absent"}:
        raise ValueError("state must be 'present' or 'absent'")
    if rebuild_on not in {"never", "config_change", "always"}:
        raise ValueError("rebuild_on must be one of: never, config_change, always")

    proxmox: dict = {
        "net": {
            "ip": _normalize_ip(ip_cidr),
            "bridge": bridge,
        }
    }
    if gateway:
        proxmox["net"]["gw"] = _strip_cidr(gateway) if "/" in gateway else gateway
    if node:
        proxmox["node"] = node
    if storage:
        proxmox["storage"] = storage
    if cores is not None:
        proxmox["cores"] = cores
    if memory is not None:
        proxmox["memory"] = memory
    if nameserver:
        proxmox["nameserver"] = nameserver
    if searchdomain:
        proxmox["searchdomain"] = searchdomain
    if onboot is not None:
        proxmox["onboot"] = onboot
    if started is not None:
        proxmox["started"] = started

    if instance_type == "lxc":
        normalized_artifact_storage = _normalize_lxc_artifact_storage(artifact_storage)
        proxmox["ostemplate"] = artifact if ":" in artifact else f"{normalized_artifact_storage}/{artifact}"
        if disk:
            proxmox["disk"] = disk
        if unprivileged is not None:
            proxmox["unprivileged"] = unprivileged
    else:
        proxmox["template_name"] = artifact

    return {
        "provider": provider,
        "type": instance_type,
        "id": instance_id,
        "state": state,
        "rebuild_on": rebuild_on,
        "proxmox": proxmox,
    }


def render_yaml_document(data: dict) -> str:
    return yaml.safe_dump({"infra": data}, sort_keys=False)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Proxmox-backed infra: YAML block for a VM or LXC.",
        epilog=help_epilog("ID", "ARTIFACT", "IP"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--provider", default=os.environ.get("PROXMOX_PROVIDER", "proxmox"))
    parser.add_argument("--type", choices=["lxc", "vm"], dest="instance_type", **parser_kwargs(suffix="TYPE", required=True))
    parser.add_argument("--id", type=int, dest="instance_id", default=env_int("ID"), required=env_int("ID") is None)
    parser.add_argument("--artifact", help="LXC template filename/ref or VM template name", **parser_kwargs(suffix="ARTIFACT", required=True))
    parser.add_argument("--ip", dest="ip_cidr", help="Primary IP with CIDR, e.g. 192.0.2.10/24", **parser_kwargs(suffix="IP", required=True))
    parser.add_argument("--gateway", **parser_kwargs(suffix="GATEWAY"))
    parser.add_argument("--bridge", **parser_kwargs(suffix="BRIDGE", default="vmbr0"))
    parser.add_argument("--state", choices=["present", "absent"], **parser_kwargs(suffix="STATE", default="present"))
    parser.add_argument("--rebuild-on", choices=["never", "config_change", "always"], **parser_kwargs(suffix="REBUILD_ON", default="never"))
    parser.add_argument("--node", **parser_kwargs(suffix="NODE"))
    parser.add_argument("--storage", **parser_kwargs(suffix="STORAGE"))
    parser.add_argument("--artifact-storage", help="Used for LXC template filenames without a storage prefix", **parser_kwargs(suffix="ARTIFACT_STORAGE", default="local:vztmpl"))
    parser.add_argument("--cores", type=int, default=env_int("CORES"))
    parser.add_argument("--memory", type=int, default=env_int("MEMORY"))
    parser.add_argument("--disk", **parser_kwargs(suffix="DISK"))
    parser.add_argument("--nameserver", **parser_kwargs(suffix="NAMESERVER"))
    parser.add_argument("--searchdomain", **parser_kwargs(suffix="SEARCHDOMAIN"))
    parser.add_argument("--onboot", action=argparse.BooleanOptionalAction, default=env_bool("ONBOOT"))
    parser.add_argument("--started", action=argparse.BooleanOptionalAction, default=env_bool("STARTED"))
    parser.add_argument("--unprivileged", action=argparse.BooleanOptionalAction, default=env_bool("UNPRIVILEGED"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    data = build_infra_config(
        provider=args.provider,
        instance_type=args.instance_type,
        instance_id=args.instance_id,
        artifact=args.artifact,
        ip_cidr=args.ip_cidr,
        gateway=args.gateway,
        bridge=args.bridge,
        state=args.state,
        rebuild_on=args.rebuild_on,
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
    )
    sys.stdout.write(render_yaml_document(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
