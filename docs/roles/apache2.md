# apache2

Runs backend Apache sites for services where `app.type: apache2`; nginx stays in front.

`group_vars` example:
```yaml
apache2_base_port: 8080
apache2_mod_rewrite: true
services:
  legacyapp:
    enabled: true
    domain: legacy.example.com
    owner: legacy
    app:
      type: apache2
      php: true
```

`host_vars` example:
```yaml
apache2_base_port: 8180
```

`vault` example:
```yaml
# No role-specific vault keys.
```
