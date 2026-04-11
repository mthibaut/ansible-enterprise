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
    web:
      upstream: http://127.0.0.1:8080
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
# No nginx-only vault keys; certbot and app secrets live elsewhere.
```
