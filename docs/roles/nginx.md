# nginx

Builds reverse-proxy or static-site vhosts from the `services` dictionary.

`group_vars` example:
```yaml
services:
  app:
    enabled: true
    domain: app.example.com
    aliases: [www.app.example.com]
    owner: app
    security:
      tls:
        enabled: true
        certificate: app.example.com
    web:
      upstream: http://127.0.0.1:8080

certificates:
  app.example.com:
    method: certbot
    domains: [app.example.com, www.app.example.com]
```

`host_vars` example:
```yaml
services:
  static:
    enabled: true
    domain: static.example.com
    owner: static
```

`vault` example:
```yaml
# No nginx-only vault keys; certificate material lives under certificates.
```

TLS paths are resolved from the selected `certificates` entry. `certbot`
certificates use Certbot's lineage directory. `inventory` and `selfsigned`
certificates use Ansible-owned files under `/etc/ssl/{certs,private}/ansible-enterprise/`
on most systems, or `/etc/pki/tls/{certs,private}/ansible-enterprise/` on
RedHat-family systems. `path` certificates use the exact paths declared in the
selected registry entry.
