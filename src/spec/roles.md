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

### nginx / nextcloud php-fpm integration

The nextcloud role installs php-fpm and starts Nextcloud via occ. It does
not configure the nginx <-> php-fpm socket because that is nginx's concern.

The nginx role is responsible for rendering the php-fpm upstream block in
vhost templates for services whose app type is nextcloud. Until that work is
done the nginx <-> php-fpm socket path is not wired end-to-end.

This boundary is intentional. Do not add nginx configuration tasks to the
nextcloud role; add a nextcloud-specific vhost template to the nginx role
instead.

Future work: roles/nginx/templates/nextcloud.conf.j2 and the corresponding
branch in roles/nginx/tasks/render_service.yml for type == 'nextcloud'.
