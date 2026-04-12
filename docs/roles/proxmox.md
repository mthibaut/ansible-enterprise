# proxmox

Configures a Proxmox VE host itself: repositories, nag removal, backups, SMTP, and host-level tuning. This is separate from `infra.yml`, which now uses the generic `infra_defaults` / `infra` model and currently supports `provider: proxmox`.

`group_vars` example:
```yaml
proxmox:
  enabled: true
  repo: no_subscription
  remove_nag: true
  backup:
    enabled: true
    storage: local
    schedule: "0 2 * * *"
    mode: snapshot
```

`host_vars` example:
```yaml
proxmox:
  smtp:
    enabled: true
    relayhost: smtp.example.net
```

`vault` example:
```yaml
# API token usage for infra.yml is usually split like this:
# infra_defaults.proxmox.api_host: 192.0.2.20   # optional override
# infra_defaults.proxmox.api_user: root@pam
# vault_proxmox_api_token_id: ansible
# vault_proxmox_api_token_secret: CHANGE_ME
# Create the API token with Privilege Separation disabled.
proxmox_smtp_password: "CHANGE_ME"
```
