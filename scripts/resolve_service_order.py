#!/usr/bin/env python3
import yaml
from collections import defaultdict, deque
data = yaml.safe_load(open('group_vars/all/main.yml')) or {}
services = data.get('services', {})
graph = defaultdict(list)
in_degree = {name: 0 for name in services}
for name, svc in services.items():
    for dep in svc.get('depends_on', []):
        if dep in services:
            graph[dep].append(name)
            in_degree[name] += 1
queue = deque(sorted([name for name, degree in in_degree.items() if degree == 0]))
order = []
while queue:
    node = queue.popleft(); order.append(node)
    for nxt in sorted(graph[node]):
        in_degree[nxt] -= 1
        if in_degree[nxt] == 0: queue.append(nxt)
if len(order) != len(services): raise SystemExit('dependency cycle detected')
for name in order: print(name)
