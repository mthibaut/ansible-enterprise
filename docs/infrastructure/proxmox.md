# Proxmox Infrastructure Provisioning

`infra.yml` creates and manages infrastructure instances from inventory.
This document covers the current `proxmox` provider implementation.
It is separate from `site.yml`, which configures hosts after they exist.

## Provider status

- `proxmox`: implemented
- `aws`: not implemented yet
- manual provisioning: supported fallback when provider automation is unavailable or unnecessary

If you are not using an implemented `infra.yml` provider, provision the host manually first and then use `site.yml` for configuration management.

## Prerequisites

Install the Python libraries on the Ansible controller, not on the PVE nodes:

```bash
pip install proxmoxer requests
```

Install the Ansible collection:

```bash
ansible-galaxy collection install community.proxmox
```

Create a Proxmox API token in the PVE web UI at `Datacenter -> Permissions -> API Tokens`.
This project keeps the Proxmox user and token name separate:

- `infra_defaults.proxmox.api_host` optionally overrides the Proxmox API endpoint if it differs from the node hostname or its `ansible_host`
- `infra_defaults.proxmox.api_user` contains the owning user, for example `root@pam`
- `vault_proxmox_api_token_id` contains only the token name, for example `ansible`

For this setup, create the token with **Privilege Separation disabled**.

Store them like this:

```yaml
infra_defaults:
  provider: proxmox
  proxmox:
    api_host: 192.0.2.20
    api_user: root@pam

vault_proxmox_api_token_id: "ansible"
vault_proxmox_api_token_secret: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## Configuration

Group-level defaults go in `group_vars/<group>/main.yml`:

```yaml
infra_defaults:
  provider: proxmox
  state: present
  rebuild_on: never
  proxmox:
    node: pve01
    # Optional if the API endpoint differs from the node inventory address.
    # If omitted, infra.yml uses hostvars[pve01].ansible_host and then pve01.
    api_host: 192.0.2.20
    api_user: root@pam
    template_vmid: 9000
    storage: local-lvm
    cores: 2
    memory: 2048
    onboot: true
    started: true
    net:
      bridge: vmbr0
      gw: 192.0.2.1
    nameserver: 192.0.2.53
    searchdomain: example.internal
```

Per-host overrides go in `host_vars/<host>/infra.yml` using `infra`.
Values are merged on top of `infra_defaults`, so you only need to specify the differences.

### VM example

```yaml
infra:
  provider: proxmox
  type: vm
  id: 110
  state: present
  rebuild_on: config_change
  proxmox:
    cores: 4
    memory: 4096
    disks:
      - size: 15G
      - size: 2000G
    net:
      ip: 192.0.2.90/24
```

### LXC example

```yaml
infra:
  provider: proxmox
  type: lxc
  id: 200
  state: present
  rebuild_on: never
  proxmox:
    ostemplate: "local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
    storage: local
    disk: 8
    cores: 1
    memory: 512
    net:
      ip: 192.0.2.91/24
```

Note:
- Using local storage for LXC root filesystems typically requires root-level Proxmox permissions. If your API token is more restricted, use a storage target and permission model that your token can actually allocate on.
- LXC `ostemplate` must come from a file-based Proxmox storage that has `Container template` content enabled. The container rootfs `storage` can still be something different, such as `local-lvm`.

## Lifecycle and rebuild policy

`infra.yml` supports both lifecycle and rebuild policy controls:

```yaml
infra_defaults:
  provider: proxmox
  state: present
  rebuild_on: never

infra:
  provider: proxmox
  state: present
  rebuild_on: config_change
```

Lifecycle values:

- `present`: ensure the guest exists
- `absent`: stop and destroy the guest if it exists, then remove cached controller-side state

Rebuild values:

- `never`: keep the existing guest and update it in place
- `config_change`: destroy and recreate the guest when the effective desired config changes
- `always`: destroy and recreate the guest on every run

The per-host `infra.state` value overrides `infra_defaults.state`.
The per-host `infra.rebuild_on` value overrides `infra_defaults.rebuild_on`.

When `state: absent`, the playbook removes the guest and skips all provisioning, startup, and SSH wait steps.

Example removal:

```yaml
infra:
  provider: proxmox
  type: vm
  id: 110
  state: absent
```

For `config_change`, the playbook stores the last applied desired config fingerprint in `build/.infra-state/<inventory_hostname>.json` on the Ansible controller. This makes rebuild decisions deterministic without requiring extra metadata inside Proxmox.

## Cloud-init behavior

SSH keys from `admin_users`, and `admin_ssh_public_key` as fallback, are injected into cloud-init even when `admin_users_enabled: false`. That keeps first-login access predictable for newly created guests.

## Usage

Provision all hosts with `infra` defined:

```bash
ansible-playbook -i inventory ansible-enterprise/build/infra.yml
```

Provision a single host:

```bash
ansible-playbook -i inventory ansible-enterprise/build/infra.yml --limit vm-example
```

Force a rebuild without changing inventory:

```bash
ansible-playbook -i inventory ansible-enterprise/build/infra.yml -e infra_force_rebuild=true --limit vm-example
```

`infra_force_rebuild=true` overrides `rebuild_on` for that run and always reprovisions the instance.

Then configure the new host with the normal site playbook:

```bash
ansible-playbook -i inventory ansible-enterprise/build/site.yml --limit vm-example
```

## Playbooks

The generated `build/` directory contains these playbooks:

| Playbook | Purpose |
| --- | --- |
| `infra.yml` | Creates, updates, or destroys infrastructure instances from inventory. Run first. |
| `lxc_bootstrap.yml` | Installs Python on minimal LXC containers via `raw` module. Run after `infra.yml` for LXC targets that lack Python. Skips hosts that already have a working interpreter. |
| `bootstrap.yml` | Generates per-host bootstrap shell scripts on the Ansible controller (connection: local). Not the same as `lxc_bootstrap.yml`. |
| `site.yml` | Configures hosts with roles. Requires a working Python interpreter on each target. |

Typical workflow:

```text
infra.yml → lxc_bootstrap.yml → site.yml
```

## Scripts

The repo includes user-facing scripts under `src/scripts/`:

| Script | Purpose |
| --- | --- |
| `proxmox_infra_render.py` | Renders a single `host_vars/<host>/infra.yml` file from CLI flags. Use for one-off host additions. |
| `proxmox_inventory_scaffold.py` | Creates `hosts.ini` and `host_vars/<host>/infra.yml` for multiple hosts from two-column stdin input (hostname + artifact). Use for bulk inventory generation. |
| `bootstrap_pull_host.sh` | Installs Ansible collections from `requirements.yml` and runs `ansible-pull` against `site.yml`. Use on a target host that pulls its own config. |
| `precommit_verify.sh` | Runs all repository contract verifications (repo contracts, services schema, checkpoints). Used by pre-commit hooks and CI. |

Scripts under `src/scripts/internal/` are not meant to be called directly.

### Inventory scaffold details

Second-column behavior depends on `--type`:

- `--type lxc`: the second column is an LXC template artifact; if it does not already include a storage prefix like `shared:vztmpl/...`, the script defaults it to `local:vztmpl/`
- `--type vm`: the second column is treated as a Proxmox VM template name and is written to `proxmox.template_name`

For LXCs, `--artifact-storage` may be either:

- a full prefix like `local:vztmpl` or `shared:vztmpl`
- or a bare storage name like `synology-pve`, which the helper normalizes to `synology-pve:vztmpl`

That storage must still be a Proxmox template-capable file storage. If Proxmox does not expose `Container template` content for it, use a storage like `local:vztmpl` for `ostemplate` and keep your rootfs destination in `proxmox.storage`.

Both scripts also support `PROXMOX_*` environment variables, and `--help` prints the full list with descriptions. A few common examples:

```bash
export PROXMOX_PROVIDER=proxmox
export PROXMOX_NODE=pve01
export PROXMOX_BRIDGE=vmbr0
export PROXMOX_GATEWAY=192.0.2.1
export PROXMOX_CORES=2
export PROXMOX_MEMORY=4096
```

Use the renderer for one host:

```bash
./src/scripts/proxmox_infra_render.py \
  --type vm \
  --id 110 \
  --artifact ubuntu-noble-ci \
  --ip 192.0.2.90/24
```

Use the scaffold script for many hosts:

```bash
./src/scripts/proxmox_inventory_scaffold.py \
  --type lxc \
  --id-start 200 \
  --ip-start 192.0.2.10/24 \
  --out-dir inventory-scaffold <<'EOF'
almalinux-10 almalinux-10-default_20250930_amd64.tar.xz
almalinux-9 almalinux-9-default_20240911_amd64.tar.xz
EOF
```

## Preparing a cloud-init VM template

One-time on the Proxmox host:

```bash
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
qm create 9000 --name ubuntu-noble-ci --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 noble-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --boot order=scsi0 --ide2 local-lvm:cloudinit
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```
