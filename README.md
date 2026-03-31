# Enterprise Ansible Platform

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
make checkpoints     # checkpoint ordering
make services        # services schema
make order           # service dependency order
```

## Generator workflow

To update a managed file:

1. Edit the file's content in `FILE_MANIFEST` inside `src/generate_ansible_enterprise.py`.
2. Run `make generate`.
3. Commit the `src/` change. `build/` is gitignored.

Files in `UNMANAGED_FILES` (e.g. `build/group_vars/all/vault.yml`) are never touched.

## Role overview

| Role | Purpose |
|---|---|
| preflight | SSH key assertion before any changes |
| common | Fast variable contract assertions |
| ssh_hardening | Hardened sshd_config; keys deployed after restart |
| geoip | MaxMind GeoLite2 download and nftables set generation |
| firewall_geo | nftables ruleset; GeoIP drops before port-accept rules |
| dns | BIND hidden primary; zone files created once, serials updated deterministically |
| certbot | DNS-01 TLS certificate provisioning via Let's Encrypt |
| nginx | Per-service vhosts from the services dict |
| users | Service owner accounts and web roots |
| nextcloud | Nextcloud + MariaDB stack |
| mailserver | Postfix + Dovecot + OpenDKIM |

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

Tag and export:

```bash
git tag checkpoint-011-src-build-separation
git archive --format=zip --prefix="ansible-enterprise-checkpoint-011-src-build-separation/" \
  checkpoint-011-src-build-separation -o ansible-enterprise-checkpoint-011-src-build-separation.zip
```
