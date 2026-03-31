<!--
GENERATED FILE - DO NOT EDIT
This file is overwritten by generate_ansible_enterprise.py.
Source of truth: PROMPT.md.
Manual edits will be lost on the next regeneration.
-->

# Services

Services are declared in `group_vars/all/main.yml` under the `services` key.

Each service can describe:
- `enabled`: bool - whether to deploy this service
- `domain`: str - the domain name served
- `owner`: str - the system user that owns the service
- `depends_on`: list - other service names this depends on
- `security`: expose_http, expose_https, tls, require_client_cert, client_ca_path
- `web`: upstream_host, upstream_port (for nginx reverse proxy)
- `app`: type, version, db_name, db_user, db_password, data_dir (for app roles)

Services drive nginx vhosts, firewall port openings, user creation, and
optional app deployment (nextcloud). Schema validated at runtime by preflight.
