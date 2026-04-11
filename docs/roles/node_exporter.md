# node_exporter

Installs Prometheus node_exporter and restricts scrape access.

`group_vars` example:
```yaml
node_exporter_enabled: true
node_exporter_port: 9100
node_exporter_scrape_addresses: [192.0.2.50]
```

`host_vars` example:
```yaml
node_exporter_enabled: false
```

`vault` example:
```yaml
# No role-specific vault keys.
```
