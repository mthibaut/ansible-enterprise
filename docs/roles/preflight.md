# preflight

Validates that bootstrap SSH access is possible before the play makes deeper changes.

Main inputs: shared admin variables from the common role.

`group_vars` example:
```yaml
admin_users: [myadmin]
deployment_environment: production
```

`host_vars` example:
```yaml
ssh_port: 49222
```

`vault` example:
```yaml
admin_ssh_public_key: "ssh-ed25519 AAAA..."
admin_dev_password_hash: "$6$..."
```
