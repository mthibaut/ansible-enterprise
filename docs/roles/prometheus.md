# prometheus

Runs Prometheus locally, usually scraping `node_exporter` plus any extra targets you define.

`group_vars` example:
```yaml
prometheus_enabled: true
prometheus_port: 9090
prometheus_scrape_interval: 15s
prometheus_scrape_targets:
  - targets: ["web01.example.com:9100"]
    labels:
      job: node
```

`host_vars` example:
```yaml
prometheus_retention: "30d"
```

`vault` example:
```yaml
# No role-specific vault keys.
```
