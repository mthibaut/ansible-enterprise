# certbot

Materializes TLS certificates requested by nginx services and mailserver.
Each consumer references a certificate by name; `certificates.<name>.method`
chooses how that certificate is produced: `selfsigned`, `certbot`, `path`,
`inventory`, or reserved `stepca`.

`group_vars` example:
```yaml
certificates:
  app.example.com:
    method: certbot
    domains: [app.example.com, www.app.example.com]
  mail.example.com:
    method: inventory
    domains: [mail.example.com]
    fullchain_pem: "{{ vault_mail_fullchain_pem }}"
    privkey_pem: "{{ vault_mail_privkey_pem }}"

certbot_email: ops@example.com
certbot_staging: false
certbot_dns_method: local
certbot_tsig_key_name: certbot-acme
```

`host_vars` example:
```yaml
certbot_staging: true
certbot_dns_method: nsupdate
certbot_tsig_server: 192.0.2.53
```

`vault` example:
```yaml
certbot_tsig_secret: "BASE64SECRET"
```

`certbot` mode obtains Let's Encrypt certificates via DNS-01, using local BIND
updates or remote `nsupdate`. `inventory` mode writes PEM material from the
`certificates` registry to the host. `path` mode consumes existing host paths
and does not copy key material.

On disk, Certbot-owned certificates stay in Certbot's native lineage store:

```text
Linux:   /etc/letsencrypt/live/<primary-domain>/fullchain.pem
Linux:   /etc/letsencrypt/live/<primary-domain>/privkey.pem
FreeBSD: /usr/local/etc/letsencrypt/live/<primary-domain>/fullchain.pem
FreeBSD: /usr/local/etc/letsencrypt/live/<primary-domain>/privkey.pem
```

Ansible-owned `inventory` and `selfsigned` material uses the target
distribution's TLS cert/private tree:

```text
Debian/Ubuntu/Arch/SUSE/FreeBSD/etc:
  /etc/ssl/certs/ansible-enterprise/<certificate-name>/fullchain.pem
  /etc/ssl/private/ansible-enterprise/<certificate-name>/privkey.pem

RedHat/Alma/Rocky/Fedora:
  /etc/pki/tls/certs/ansible-enterprise/<certificate-name>/fullchain.pem
  /etc/pki/tls/private/ansible-enterprise/<certificate-name>/privkey.pem
```

`path` material is never moved; the selected certificate uses the exact
`fullchain_path`/`privkey_path` declared in `certificates`.
