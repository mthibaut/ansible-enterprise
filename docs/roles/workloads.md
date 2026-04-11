# workloads

Runs OCI containers from the `workloads` list using the selected container engine.

`group_vars` example:
```yaml
container_engine: podman
workloads:
  - name: whoami
    image: traefik/whoami
    ports: ["8080:80"]
    restart: always
```

`host_vars` example:
```yaml
workloads:
  - name: app
    image: ghcr.io/example/app:latest
    volumes:
      - /srv/app:/data
    env:
      TZ: Europe/Brussels
```

`vault` example:
```yaml
# Put secret env values in vault and reference them in workloads[].env.
```
