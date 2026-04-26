<!--
GENERATED FILE - DO NOT EDIT
This file is overwritten by generate_ansible_enterprise.py.
Source of truth: PROMPT.md.
Manual edits will be lost on the next regeneration.
-->

# Roles

Current role set:

- common        - fast variable contract assertions (fails before any changes)
- preflight     - schema validation + SSH key check before any system changes
- ssh_hardening - hardened sshd_config, key deployment after sshd restart
- geoip         - MaxMind GeoLite2 CSV download + nftables set generation
- firewall_geo  - nftables ruleset with GeoIP drop rules before port-accept rules
- dns           - BIND hidden-primary; zone files created once, serials updated
- nginx         - installs nginx, renders per-service vhosts from services dict
- users         - creates service owner accounts and web roots
- certbot       - DNS-01 TLS certificate provisioning via Let's Encrypt
- nextcloud     - Nextcloud + MariaDB stack (conditional on services.nextcloud)
- mailserver    - Postfix + Dovecot + OpenDKIM (conditional on mailserver.enabled)

## Protected roles

firewall_geo, mailserver, and nextcloud contain critical infrastructure logic
and are in the Protected Logic Zone. Their file counts and task presence are
verified by CI.

## Role scope boundaries

### certbot DNS prerequisite

The certbot role provisions certificates via DNS-01. Let's Encrypt validates
by querying public authoritative DNS for `_acme-challenge.<domain> TXT`.

Ansible runs the dns role before certbot, so BIND is installed and running.
However Ansible cannot set registrar NS records. Before the first run the
operator must ensure the domain's NS records at the registrar already
delegate to this host (when certbot_dns_local=true) or to the external
DNS provider. Without this, Let's Encrypt cannot reach the authoritative
nameserver and the challenge fails.

The certbot role includes a dig pre-flight check that fails fast with a
clear error if the domain does not resolve to this host before attempting
certificate issuance.

### nginx / nextcloud FPM integration

The nextcloud role deploys a Docker Compose stack with a `nextcloud:fpm`
application container listening on `127.0.0.1:{{ nextcloud_fpm_port }}`.
It does not configure nginx because that is nginx's concern.

The nginx role renders `roles/nginx/templates/nextcloud.conf.j2` for
services whose app type is `nextcloud`. That template serves static files
from `nextcloud_install_dir` and proxies PHP requests to the Nextcloud FPM
container over TCP.

This boundary is intentional. Do not add nginx configuration tasks to the
nextcloud role; keep HTTP vhost rendering in the nginx role.
