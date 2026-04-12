#!/usr/bin/env python3
"""
derive_dns_zones.py — compute the effective BIND zone list.

The DNS role builds its zone list from two sources:

  1. dns_hidden_primary_zones  — explicitly declared zones (may be empty).
  2. services                  — enabled service domains are added as zones
                                 if they are not already covered by a declared
                                 zone (exact apex match or subdomain of one).

A service domain is "covered" when:
  - it equals a declared zone exactly  (example.com == example.com), OR
  - it is a subdomain of a declared zone  (app.example.com ⊆ example.com).

Covered domains contribute A records inside the parent zone (via zone.db.j2)
rather than becoming separate zones.

This module is the canonical Python reference for the derive logic.  The same
algorithm is implemented as a Jinja2 set_fact expression in
roles/dns/tasks/main.yml.  Both must be kept in sync.

Usage (standalone):
    python3 derive_dns_zones.py --vars-file build/group_vars/all/main.yml
"""

import argparse
import pathlib
import sys
from typing import Dict, List, Any


def derive_zones(declared_zones: List[str], services: Dict[str, Any]) -> List[str]:
    """Return the effective DNS zone list.

    Parameters
    ----------
    declared_zones:
        Contents of ``dns_hidden_primary_zones`` from group_vars.
    services:
        Contents of the ``services`` dict from group_vars.

    Returns
    -------
    Sorted, deduplicated list of zone names (declared + auto-derived).
    """
    extra: List[str] = []
    for svc in services.values():
        if not svc.get("enabled", False):
            continue
        domain = svc.get("domain", "")
        if not domain:
            continue
        covered = any(
            domain == zone or domain.endswith("." + zone)
            for zone in declared_zones
        )
        if not covered and domain not in extra and domain not in declared_zones:
            extra.append(domain)

    return sorted(set(declared_zones) | set(extra))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vars-file",
                    default="build/group_vars/all/main.yml",
                    help="Path to group_vars/all/main.yml (default: %(default)s)")
    args = ap.parse_args()

    try:
        import yaml  # type: ignore
    except ImportError:
        print("error: PyYAML is required (pip install PyYAML)", file=sys.stderr)
        sys.exit(1)

    vars_path = pathlib.Path(args.vars_file)
    if not vars_path.exists():
        print(f"error: {vars_path} not found — run 'make generate' first",
              file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(vars_path.read_text(encoding="utf-8"))
    declared = data.get("dns_hidden_primary_zones", []) or []
    services = data.get("services", {}) or {}

    zones = derive_zones(declared, services)
    for z in zones:
        print(z)


if __name__ == "__main__":
    main()
