# certbot

Obtains Let's Encrypt certificates via DNS-01, using local BIND updates or remote `nsupdate`.

`group_vars` example:
```yaml
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
