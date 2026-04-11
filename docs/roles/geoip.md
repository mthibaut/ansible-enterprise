# geoip

Downloads GeoLite2 data and builds country/IP sets consumed by the firewall role.

`group_vars` example:
```yaml
geoip:
  enabled: true
  allowed_countries: [BE, NL, DE]
  ssh_allowed_countries: [BE, NL]
```

`host_vars` example:
```yaml
geoip:
  enabled: true
  allowed_countries: [BE]
```

`vault` example:
```yaml
geoip_enabled: true
geoip_license_key: "YOUR_MAXMIND_KEY"
geoip_allowed_countries: [BE, NL, DE]
geoip_ssh_allowed_countries: [BE, NL]
geoip_allowlist_entries: [192.168.0.0/16]
```
