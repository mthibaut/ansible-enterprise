# docker

Provides Docker runtime support for dependent roles such as Nextcloud, Prometheus, and Grafana. In newer configurations, prefer the more explicit `container_engine` role when you want to choose between Podman and Docker.

`group_vars` example:
```yaml
# No standalone docker role variables are documented here.
# Prefer:
container_engine: docker
```

`host_vars` example:
```yaml
container_engine: docker
```

`vault` example:
```yaml
# No role-specific vault keys.
```
