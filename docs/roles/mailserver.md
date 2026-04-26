# mailserver

Configures Postfix, Dovecot, and OpenDKIM from flat `mailserver_*` variables.

`group_vars` example:
```yaml
mailserver_enabled: true
mailserver_domain: mail.example.com
mailserver_admin_mail_user: mailadmin
mailserver_local_domains: [example.com]
mailserver_relay_domains: []
mailserver_ports: [25, 587]
mailserver_tls_enabled: true
mailserver_tls_certificate: mail.example.com

certificates:
  mail.example.com:
    method: inventory
    domains: [mail.example.com]
    fullchain_pem: "{{ vault_mail_fullchain_pem }}"
    privkey_pem: "{{ vault_mail_privkey_pem }}"
```

`host_vars` example:
```yaml
mailserver_masquerading_enabled: true
mailserver_masquerade_domains: [example.com]
mailserver_masquerade_users: [alerts]
```

`vault` example:
```yaml
mailserver_admin_password: "CHANGE_ME"
vault_mail_fullchain_pem: |
  -----BEGIN CERTIFICATE-----
  ...
  -----END CERTIFICATE-----
vault_mail_privkey_pem: |
  -----BEGIN PRIVATE KEY-----
  ...
  -----END PRIVATE KEY-----
```

`mailserver_ports` is the firewall source of truth for exposed mail listeners.
Default is `[25, 587, 143, 465]`. Override it per host if a system should only
expose a subset, for example SMTP plus submission only. `mailserver_open_ports`
remains a deprecated compatibility alias.

When `mailserver_tls_enabled` is true, Postfix and Dovecot use the certificate
selected by `mailserver_tls_certificate`. The certificate entry is declared in
the host-level `certificates` registry. Its `method` decides whether it is
produced by `selfsigned` or `certbot`, copied from inventory PEM material, or
referenced by existing paths.

Certbot certificates are consumed from Certbot's lineage directory. Inventory
and self-signed mail certificates are written under the native TLS tree, for
example `/etc/ssl/private/ansible-enterprise/mail.example.com/privkey.pem` on
Debian-like systems or
`/etc/pki/tls/private/ansible-enterprise/mail.example.com/privkey.pem` on
RedHat-family systems.
