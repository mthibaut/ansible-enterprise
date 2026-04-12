#!/usr/bin/env python3
"""
resolve_capabilities.py -- compute the set of provider roles required by
enabled services.

The capabilities layer maps platform capability names (e.g. "tls", "mail")
to the provider role that satisfies each one (e.g. "nginx", "mailserver").
Each service may declare a ``requires`` list of capability names. This module
collects every capability required by any enabled service, resolves each name
through the capabilities dict, and returns the deduplicated sorted list of
provider role names.

This Python module is the canonical reference for the resolve logic.  The same
algorithm is expressed as a Jinja2 set_fact expression in site.yml pre_tasks.
Both must be kept in sync.

Usage (standalone):
    python3 resolve_capabilities.py --vars-file build/group_vars/all/main.yml
"""

import argparse
import pathlib
import sys
from typing import Any, Dict, List


def resolve_providers(
    capabilities: Dict[str, Any],
    services: Dict[str, Any],
) -> List[str]:
    """Return the sorted list of provider role names required by enabled services.

    Parameters
    ----------
    capabilities:
        The ``capabilities`` dict from group_vars (maps name -> {provider: role}).
    services:
        The ``services`` dict from group_vars.

    Returns
    -------
    Sorted, deduplicated list of provider role name strings.
    Unknown capability names (not in capabilities dict) are silently skipped;
    CI enforces that every ``requires`` entry resolves via
    verify_capability_contracts().
    """
    providers: set = set()
    for svc in services.values():
        if not svc.get("enabled", False):
            continue
        for cap_name in svc.get("requires", []):
            cap = capabilities.get(cap_name)
            if cap and isinstance(cap, dict) and cap.get("provider"):
                providers.add(cap["provider"])
    return sorted(providers)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--vars-file",
        default="build/group_vars/all/main.yml",
        help="Path to group_vars/all/main.yml (default: %(default)s)",
    )
    args = ap.parse_args()

    try:
        import yaml  # type: ignore
    except ImportError:
        print("error: PyYAML is required (pip install PyYAML)", file=sys.stderr)
        sys.exit(1)

    vars_path = pathlib.Path(args.vars_file)
    if not vars_path.exists():
        print(
            f"error: {vars_path} not found -- run 'make generate' first",
            file=sys.stderr,
        )
        sys.exit(1)

    data = yaml.safe_load(vars_path.read_text(encoding="utf-8"))
    capabilities = data.get("capabilities", {}) or {}
    services = data.get("services", {}) or {}

    for role in resolve_providers(capabilities, services):
        print(role)


if __name__ == "__main__":
    main()
