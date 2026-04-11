# container_engine

Selects and installs the host container runtime used by the `workloads` role.

`group_vars` example:
```yaml
container_engine: podman
container_engine_registries: [docker.io, quay.io]
```

`host_vars` example:
```yaml
container_engine: docker
container_engine_compose: true
container_engine_docker_edition: ce
```

`vault` example:
```yaml
# No role-specific vault keys.
```
