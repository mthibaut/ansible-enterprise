# Enterprise Ansible Platform

[![CI](https://github.com/mthibaut/ansible-enterprise/actions/workflows/ci.yml/badge.svg)](https://github.com/mthibaut/ansible-enterprise/actions/workflows/ci.yml)

Deterministic Ansible platform for provisioning and configuring hardened Linux servers.
Supports Debian 12/13, Ubuntu 24.04/25.04, AlmaLinux 9/10, Rocky Linux 9/10, Alpine, Arch, openSUSE, Fedora, Gentoo, Devuan, and FreeBSD.

## Two modes of operation

This platform has two distinct phases that run independently:

**Phase 1 -- Infrastructure provisioning** creates the hosts themselves.
Runs from the Ansible controller against the hypervisor API. No SSH to the target is needed.

```text
infra.yml → lxc_bootstrap.yml → (hosts now exist and have Python)
```

**Phase 2 -- Host configuration** installs and configures services on existing hosts.
Runs from the Ansible controller over SSH (or `pct exec` for LXC) to the target.

```text
site.yml → (hosts are now fully configured)
```

You can use either phase independently. If your hosts already exist (bare metal, cloud VMs, manually provisioned), skip Phase 1 and go straight to `site.yml`.

## Repository layout

```text
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

Install dependencies:

```bash
cd build
ansible-galaxy collection install -r requirements.yml
pip install jsonschema pyyaml
```

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

### Phase 1: Infrastructure provisioning (optional)

Only needed if you want Ansible to create the hosts. Currently supports Proxmox; manual provisioning is the fallback for other providers.

```bash
# Extra dependencies for Proxmox provider
pip install proxmoxer requests
ansible-galaxy collection install community.proxmox

# Create hosts
ansible-playbook -i inventory/hosts.ini infra.yml

# Install Python on minimal LXC containers (skip for VMs with cloud-init)
ansible-playbook -i inventory/hosts.ini lxc_bootstrap.yml

# Or run infrastructure provisioning, LXC bootstrap, and host configuration
# as one workflow when the inventory is complete:
ansible-playbook -i inventory/hosts.ini full-setup.yml --ask-vault-pass
```

See [Proxmox infrastructure provisioning](docs/infrastructure/proxmox.md) for full details, inventory format, lifecycle controls, and helper scripts.

### Phase 2: Host configuration

```bash
ansible-playbook -i inventory/hosts.ini site.yml --ask-vault-pass

# Minimal baseline only: preflight, common, and SSH hardening
ansible-playbook -i inventory/hosts.ini baseline.yml --ask-vault-pass
```

### Pull mode

For hosts that pull their own configuration:

```bash
bash scripts/bootstrap_pull_host.sh
```

## Playbooks

| Playbook | Phase | Purpose |
| --- | --- | --- |
| `infra.yml` | 1 | Create, update, or destroy infrastructure instances from inventory |
| `lxc_bootstrap.yml` | 1 | Install Python on minimal LXC containers via `raw` module |
| `full-setup.yml` | 1+2 | Run `infra.yml`, `lxc_bootstrap.yml`, then `site.yml` |
| `baseline.yml` | 2 | Apply only preflight, common, and SSH hardening |
| `bootstrap.yml` | 1 | Generate per-host bootstrap shell scripts on the controller |
| `site.yml` | 2 | Configure hosts with roles (requires Python on targets) |

## Validation

```bash
make validate        # all contract checks
make test            # unit tests
make checkpoints     # checkpoint ordering
make services        # services schema
make order           # service dependency order
```

## Role overview

Per-role configuration docs live under [`docs/roles/`](docs/roles/README.md).

| Role | Purpose |
| --- | --- |
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

## WireGuard boundary

`ansible-enterprise` should treat WireGuard topology rendering as a separate
concern from infrastructure deployment.

- The standalone `wireguard` project is the right place to publish topology
  parsing, key lifecycle, `wg-quick` rendering, and netplan rendering.
- `ansible-enterprise` is the right place to publish host deployment:
  package install, service enablement, firewall integration, and inventory
  consumption via `wireguard_instances`.

If both repositories are kept, prefer `wireguard` as the source of truth for
topology-driven output and keep `ansible-enterprise` focused on consuming and
deploying that output.

## Services

Services are declared in `build/group_vars/all/main.yml` and drive nginx vhosts,
firewall ports, and user creation. See `src/schemas/services.schema.json` for the
full schema and `src/spec/services.md` for documentation.

## Generator workflow

To update a managed file:

1. Edit the file's content in `FILE_MANIFEST` inside `src/generate_ansible_enterprise.py`.
2. Run `make generate`.
3. Commit the `src/` change. `build/` is gitignored.

Files in `UNMANAGED_FILES` (e.g. `build/group_vars/all/vault.yml`) are never touched.

## DNS notes

- Edit DNS behavior in `src/`, not `build/`.
- The `dns` role is authoritative-oriented. It does not try to provision a recursive/caching resolver.
- Primary zones support `overwrite: true` to let Ansible rewrite the zone file from inventory content.
- When overwriting, the role preserves the current SOA serial and only bumps it if the zone actually changed.
- SOA serials use `YYYYMMDDNN` and must stay within the DNS 32-bit serial range.
- Out-of-range legacy serials fail hard and must be repaired manually; they are not silently reset downward.
- SOA mailbox values are emitted in DNS RNAME form, not mailbox form. For example,
  `hostmaster@example.com` becomes `hostmaster.example.com.`
- Service entries support `aliases:`; aliases feed nginx `server_name`, DNS A-record derivation, and TLS SAN handling.

## Search domain management

`set_domain_name` is backend-aware. The common role routes search-domain
configuration through the active manager instead of assuming `/etc/resolv.conf`
is authoritative.

Available backends: `auto`, `networkmanager`, `systemd-resolved`, `resolvconf`, `dhclient`, `static`.

`auto` prefers: NetworkManager -> systemd-resolved -> resolvconf -> dhclient -> direct `/etc/resolv.conf`.

## Acknowledgements

This project was made possible with help from multiple AI resources used during design, implementation, validation, and handoff.
