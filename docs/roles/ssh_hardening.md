# ssh_hardening

Manages admin Unix users, sudo access, authorized keys, and `sshd_config`.

`group_vars` example:
```yaml
ssh_port: 22
sudo_enabled: true
admin_users:
  - alice
  - name: bob
    groups: [docker]
    ssh_keys:
      - ssh-ed25519 AAAA... bob@laptop
```

`host_vars` example:
```yaml
ssh_port: 49222
admin_users:
  - name: infra
    shell: /bin/bash
```

`vault` example:
```yaml
admin_ssh_public_key: "ssh-ed25519 AAAA..."
admin_dev_password_hash: "$6$..."
```
