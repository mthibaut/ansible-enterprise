# users

Creates generic local accounts from `user_accounts` and service owner accounts derived from `services`.

`group_vars` example:
```yaml
user_accounts:
  - name: deploy
    groups: [docker]
    sudo: true
  - name: appuser
    system: true
    create_home: false
```

`host_vars` example:
```yaml
user_accounts:
  - name: backup
    uid: 2500
    home: /srv/backup
```

`vault` example:
```yaml
# Use hashed passwords only if needed.
# user_accounts[].password typically comes from vault values.
vault_backup_password_hash: "$6$..."
```
