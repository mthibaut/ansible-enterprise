# Enterprise Ansible Platform

[![CI](https://github.com/mthibaut/ansible-enterprise/actions/workflows/ci.yml/badge.svg)](https://github.com/mthibaut/ansible-enterprise/actions/workflows/ci.yml)

Deterministic Ansible platform for provisioning hardened Linux servers.
Supports Debian 12/13, Ubuntu 24.04, AlmaLinux 9, and Rocky Linux 9.

## Repository layout

```
src/        Generator, specs, schemas, scripts (committed, source of truth)
build/      Generated Ansible runtime (gitignored, regenerated from src/)
Makefile    Build automation
```

The `src/` directory is the only thing you commit. `build/` is produced by
running `make generate` and is never committed.

## Quick start

Generate the Ansible runtime:

```bash
make generate
```

Install Ansible dependencies:

```bash
cd build
ansible-galaxy collection install -r requirements.yml
pip install jsonschema pyyaml
```

Optional controller-side dependencies:

```bash
# Infrastructure provisioning via infra.yml (current provider: proxmox)
pip install proxmoxer requests
ansible-galaxy collection install community.proxmox

# If you validate or render extra inventory tooling locally, keep PyYAML/jsonschema installed
```

Infrastructure provisioning docs:

- [Proxmox infrastructure provisioning](docs/infrastructure/proxmox.md)

Provider status:

- `proxmox`: implemented
- `aws`: not implemented yet
- manual provisioning: supported fallback when infra automation is unavailable or unnecessary

For manually provisioned hosts, skip `infra.yml` and run `site.yml` after the machine already exists and is reachable by Ansible.

Copy and populate the vault:

```bash
cd build
cp group_vars/all/vault.yml.example group_vars/all/vault.yml
# Set admin_ssh_public_key and ssh_port at minimum
ansible-vault encrypt group_vars/all/vault.yml
```

Copy and edit the inventory:

```bash
cd build
cp inventory/hosts.ini.example inventory/hosts.ini
```

Run the playbook from `build/`:

```bash
cd build
ansible-playbook -i inventory/hosts.ini site.yml --ask-vault-pass
```

## Pull mode

```bash
cd build
bash scripts/bootstrap_pull_host.sh
```

## Validation

```bash
make validate        # all contract checks
make test            # unit tests
make checkpoints     # checkpoint ordering
make services        # services schema
make order           # service dependency order
```

Repository-facing helper tools live in `src/scripts/`.
Generator, contract, and canonical-reference internals live in `src/scripts/internal/`.

## DNS notes

- Edit DNS behavior in `src/`, not `build/`.
- Primary zones support `overwrite: true` to let Ansible rewrite the zone file from inventory content.
- When overwriting, the role preserves the current SOA serial and only bumps it if the zone actually changed.
- SOA serials use `YYYYMMDDNN` and must stay within the DNS 32-bit serial range.
- Out-of-range legacy serials fail hard and must be repaired manually; they are not silently reset downward.
- SOA mailbox values are emitted in DNS RNAME form, not mailbox form. For example,
  `hostmaster@example.com` becomes `hostmaster.example.com.`
- Service entries support `aliases:`; aliases feed nginx `server_name`, DNS A-record derivation, and TLS SAN handling.

## Search domain management

`set_domain_name` is backend-aware. The common role now routes search-domain
configuration through the active manager instead of assuming `/etc/resolv.conf`
is authoritative.

Available backends:

- `auto`
- `networkmanager`
- `systemd-resolved`
- `resolvconf`
- `dhclient`
- `static`

`auto` prefers: NetworkManager -> systemd-resolved -> resolvconf -> dhclient -> direct `/etc/resolv.conf`.

## Generator workflow

To update a managed file:

1. Edit the file's content in `FILE_MANIFEST` inside `src/generate_ansible_enterprise.py`.
2. Run `make generate`.
3. Commit the `src/` change. `build/` is gitignored.

Files in `UNMANAGED_FILES` (e.g. `build/group_vars/all/vault.yml`) are never touched.

## Infrastructure provisioning

Infrastructure creation and lifecycle docs are kept separate from host configuration docs.

- [Proxmox infrastructure provisioning](docs/infrastructure/proxmox.md)

## Role overview

Per-role configuration docs live under [`docs/roles/`](docs/roles/README.md).

| Role | Purpose |
|---|---|
| [preflight](docs/roles/preflight.md) | SSH key assertion before any changes |
| [common](docs/roles/common.md) | Global contract validation and shared host settings |
| [ssh_hardening](docs/roles/ssh_hardening.md) | Hardened sshd_config, admin users, sudo |
| [users](docs/roles/users.md) | Generic user account management and service owner accounts |
| [geoip](docs/roles/geoip.md) | MaxMind GeoLite2 download and country/IP set generation |
| [firewall_geo](docs/roles/firewall_geo.md) | nftables or pf rules derived from geoip and exposed services |
| [dns](docs/roles/dns.md) | BIND hidden primary, explicit zones, service-derived records |
| [certbot](docs/roles/certbot.md) | DNS-01 TLS certificate provisioning via Let's Encrypt |
| [apache2](docs/roles/apache2.md) | Backend Apache vhosts for services with `app.type: apache2` |
| [nginx](docs/roles/nginx.md) | Per-service reverse proxy and static site vhosts |
| [nextcloud](docs/roles/nextcloud.md) | Nextcloud + MariaDB stack |
| [mailserver](docs/roles/mailserver.md) | Postfix + Dovecot + OpenDKIM |
| [node_exporter](docs/roles/node_exporter.md) | Host metrics exporter |
| [docker](docs/roles/docker.md) | Docker runtime support for dependent roles |
| [prometheus](docs/roles/prometheus.md) | Prometheus server |
| [grafana](docs/roles/grafana.md) | Grafana dashboards |
| [openvpn](docs/roles/openvpn.md) | Multi-instance OpenVPN |
| [wireguard](docs/roles/wireguard.md) | Multi-instance WireGuard |
| [step_ca](docs/roles/step_ca.md) | Internal ACME-compatible certificate authority |
| [samba](docs/roles/samba.md) | Samba server and shares |
| [nfs](docs/roles/nfs.md) | NFS server, client, and generic mounts |
| [container_engine](docs/roles/container_engine.md) | Podman/Docker runtime selector |
| [workloads](docs/roles/workloads.md) | OCI container workload runner |
| [bootstrap_scripts](docs/roles/bootstrap_scripts.md) | Per-host bootstrap script generation |
| [proxmox](docs/roles/proxmox.md) | Proxmox VE host configuration |
| [pfsense](docs/roles/pfsense.md) | pfSense config management |
| [file_copy](docs/roles/file_copy.md) | Copy inline or repo-managed files to targets |

## Services

Services are declared in `build/group_vars/all/main.yml` and drive nginx vhosts,
firewall ports, and user creation. See `src/schemas/services.schema.json` for the
full schema and `src/spec/services.md` for documentation.

## Checkpoints

Current documented checkpoints are listed in `src/spec/checkpoints.md`.

Validate with:

```bash
make checkpoints
```

## Acknowledgements

This project was made possible with help from multiple AI resources used during design, implementation, validation, and handoff.
