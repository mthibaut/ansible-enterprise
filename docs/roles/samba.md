# samba

Exports Samba shares and creates Samba users backed by existing Unix accounts.

`group_vars` example:
```yaml
samba:
  enabled: true
  workgroup: HOME
  shares:
    - name: data
      path: /srv/samba/data
      valid_users: [alice]
      writable: true
  users:
    - name: alice
```

`host_vars` example:
```yaml
samba:
  interfaces: [lo, eth0]
  hosts_allow: [192.0.2.0/24]
```

`vault` example:
```yaml
samba_password_alice: "CHANGE_ME"
```
