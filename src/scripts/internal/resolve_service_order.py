#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# PROTECTED IMPLEMENTATION FILE
# Changes to this file must preserve repository contracts.
# See: spec/contracts.md and spec/ai-development-mode.md.
# This file is validated by CI.
# -----------------------------------------------------------------------------
# Topological sort of services dict; prints names in dependency order.
# Raises SystemExit on dependency cycles.
from __future__ import annotations
from collections import defaultdict, deque
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[3]
BUILD = REPO / "build"


def resolve_order(services: dict) -> list:
    """Return service names in topological dependency order.
    Raises SystemExit on dependency cycles."""
    graph = defaultdict(list)
    in_degree = {name: 0 for name in services}
    for name, svc in services.items():
        for dep in svc.get("depends_on", []):
            if dep in services:
                graph[dep].append(name)
                in_degree[name] += 1
    queue = deque(sorted([n for n, d in in_degree.items() if d == 0]))
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in sorted(graph[node]):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(services):
        raise SystemExit("dependency cycle detected")
    return order


if __name__ == "__main__":
    data = yaml.safe_load((BUILD / "group_vars/all/main.yml").read_text(encoding="utf-8")) or {}
    for name in resolve_order(data.get("services", {})):
        print(name)
