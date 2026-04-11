# nextcloud

Deploys the Nextcloud stack and its MariaDB dependency.

`group_vars` example:
```yaml
nextcloud_version: "29-fpm-alpine"
nextcloud_install_dir: /var/www/nextcloud
nextcloud_compose_dir: /opt/nextcloud
```

`host_vars` example:
```yaml
nextcloud_fpm_port: 9000
nextcloud_cron_interval: "*/5"
```

`vault` example:
```yaml
nextcloud_admin_password: "CHANGE_ME"
nextcloud_db_password: "CHANGE_ME"
nextcloud_db_root_password: "CHANGE_ME"
```
