# step_ca

Runs an internal ACME-compatible CA and can optionally trust its root certificate on clients.

`group_vars` example:
```yaml
step_ca:
  enabled: true
  name: "Internal CA"
  dns_names: [ca.example.internal, 192.0.2.10]
  acme_provisioner: acme
  trust_root: false
```

`host_vars` example:
```yaml
step_ca:
  enabled: true
  address: "0.0.0.0:9000"
```

`vault` example:
```yaml
step_ca_password: "CHANGE_ME"
```
