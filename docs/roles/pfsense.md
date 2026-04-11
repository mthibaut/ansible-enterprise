# pfsense

Manages pfSense DNS overrides, DHCP static mappings, and aliases on pfSense hosts.

`group_vars` example:
```yaml
pfsense:
  enabled: true
  dns_overrides:
    - host: nas
      domain: example.internal
      ip: 192.0.2.9
  aliases:
    - name: trusted_hosts
      type: host
      addresses: [192.0.2.10, 192.0.2.11]
```

`host_vars` example:
```yaml
pfsense:
  dhcp_static_maps:
    lan:
      - mac: "aa:bb:cc:dd:ee:ff"
        ip: 192.0.2.100
        hostname: workstation
```

`vault` example:
```yaml
# No role-specific vault keys by default.
```
