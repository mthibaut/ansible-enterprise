# common

Defines the shared host-level contract: admin accounts, hostname, search domain, deployment mode, service capability map, and global toggles.

`group_vars` example:
```yaml
ssh_port: 22
admin_users:
  - name: alice
    shell: /bin/zsh
set_hostname: web01
set_domain_name: example.internal
set_domain_backend: auto
deployment_environment: production
```

`host_vars` example:
```yaml
set_hostname: mail01
set_domain_backend: networkmanager
firewall_enabled: true
```

`vault` example:
```yaml
admin_ssh_public_key: "ssh-ed25519 AAAA..."
admin_dev_password_hash: "$6$..."
```
