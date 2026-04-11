# dns

Manages BIND configuration, TSIG keys, explicit zone files, and service-derived records.

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
