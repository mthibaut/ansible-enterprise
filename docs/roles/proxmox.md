# proxmox

Configures a Proxmox VE host itself: repositories, nag removal, API-managed
backup jobs, SMTP, and host-level tuning. This is separate from `infra.yml`,
which now uses the generic `infra_defaults` / `infra` model and currently
supports `provider: proxmox`.

Backup jobs are managed through the Proxmox `/cluster/backup` API using the
`mthibaut.proxmox` collection on the Ansible controller. Install the generated
`requirements.yml` collections and make sure `proxmoxer` is available on the
controller.

`group_vars` example:
```yaml
proxmox:
  enabled: true
  repo: no_subscription
  remove_nag: true
  is_clustered: true
  api:
    user: root@pam
    token_id: ansible
    host: pve01.example.internal
    validate_certs: true
  backup_jobs:
    daily-all:
      schedule: "02:00"
      storage: backup-store
      selection_mode: all
      mode: snapshot
      compress: zstd
      prune_backups: "keep-last=7,keep-weekly=4"
      enabled: true
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
proxmox_api_token_secret: "CHANGE_ME"
proxmox_smtp_password: "CHANGE_ME"
```

Each backup job key becomes an API job ID prefixed by
`proxmox.backup_jobs_prefix`, which defaults to `ansible-`. The example above
manages `ansible-daily-all`. Job management is additive-only: removing a job
from YAML does not delete it from Proxmox. Use `state: absent` on a specific
entry when you intentionally want to remove that job.
