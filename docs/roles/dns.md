# dns

Manages authoritative BIND configuration, TSIG keys, explicit zone files, and service-derived records.

This role is intentionally not a recursive resolver/caching nameserver role. It is aimed at authoritative service for the zones you declare here. If you want a recursing nameserver, that should be a separate future workflow/role rather than an extension of this one.

See also: [dns-install-layout.md](dns-install-layout.md) for a repo-vs-package matrix of distro-specific BIND/named paths and defaults.

`group_vars` example:
```yaml
dns:
  enabled: true
  tsig_keys:
    - name: certbot-acme
      algorithm: hmac-sha512
  zones:
    - name: example.com
      type: primary
      overwrite: true
      services_auto_derive: true
      records:
        - name: "@"
          type: A
          value: 192.0.2.10
```

`host_vars` example:
```yaml
dns:
  enabled: true
  listen_on: ["127.0.0.1", "192.0.2.10"]
```

`vault` example:
```yaml
dns_tsig_certbot_acme_secret: "BASE64SECRET"
```
