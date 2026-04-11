# mailserver

Configures Postfix, Dovecot, and OpenDKIM from flat `mailserver_*` variables.

`group_vars` example:
```yaml
mailserver_enabled: true
mailserver_domain: mail.example.com
mailserver_admin_mail_user: mailadmin
mailserver_local_domains: [example.com]
mailserver_relay_domains: []
```

`host_vars` example:
```yaml
mailserver_masquerading_enabled: true
mailserver_masquerade_domain: example.com
mailserver_masquerade_users: [alerts]
```

`vault` example:
```yaml
mailserver_admin_password: "CHANGE_ME"
```
