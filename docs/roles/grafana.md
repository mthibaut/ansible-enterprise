# grafana

Runs Grafana locally, typically in front of Prometheus.

`group_vars` example:
```yaml
grafana_enabled: true
grafana_port: 3000
grafana_prometheus_url: "http://127.0.0.1:9090"
grafana_org_name: "Ansible Enterprise"
```

`host_vars` example:
```yaml
grafana_data_dir: /var/lib/grafana
```

`vault` example:
```yaml
grafana_admin_password: "CHANGE_ME"
```
