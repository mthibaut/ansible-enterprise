# firewall_geo

Applies host firewall rules using nftables on Linux and pf on FreeBSD. It consumes `geoip`, `services`, and other role inputs rather than a large standalone config block.

`group_vars` example:
```yaml
firewall_enabled: true
services:
  web:
    enabled: true
    domain: web.example.com
    security:
      expose_https: true
      geoip_allowed_countries: [BE, NL]
```

`host_vars` example:
```yaml
firewall_enabled: false
```

`vault` example:
```yaml
geoip_allowlist_entries: [10.0.0.0/8]
```
