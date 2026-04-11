# Proxmox Infrastructure Provisioning

`infra.yml` creates and manages Proxmox VMs and LXC containers from inventory.
It is separate from `site.yml`, which configures hosts after they exist.

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

- `proxmox_defaults.api_user` contains the owning user, for example `root@pam`
- `vault_proxmox_api_token_id` contains only the token name, for example `ansible`

For this setup, create the token with **Privilege Separation disabled**.

Store them like this:

```yaml
proxmox_defaults:
  api_user: root@pam

vault_proxmox_api_token_id: "ansible"
vault_proxmox_api_token_secret: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## Configuration

Group-level defaults go in `group_vars/<group>/main.yml`:

```yaml
proxmox_defaults:
  node: pve01
  api_user: root@pam
  template_vmid: 9000
  storage: local-lvm
  state: present
  rebuild_on: never
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

Per-host overrides go in `host_vars/<host>/infra.yml` using `proxmox_vm`.
Values are merged on top of `proxmox_defaults`, so you only need to specify the differences.

### VM example

```yaml
proxmox_vm:
  type: vm
  vmid: 110
  state: present
  rebuild_on: config_change
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
proxmox_vm:
  type: lxc
  vmid: 200
  state: present
  rebuild_on: never
  ostemplate: "local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst"
  disk: local:8
  cores: 1
  memory: 512
  net:
    ip: 192.0.2.91/24
```

Note:
- Using local storage for LXC root filesystems typically requires root-level Proxmox permissions. If your API token is more restricted, use a storage target and permission model that your token can actually allocate on.

## Lifecycle and rebuild policy

`infra.yml` supports both lifecycle and rebuild policy controls:

```yaml
proxmox_defaults:
  state: present
  rebuild_on: never

proxmox_vm:
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

The per-host `proxmox_vm.state` value overrides `proxmox_defaults.state`.
The per-host `proxmox_vm.rebuild_on` value overrides `proxmox_defaults.rebuild_on`.

When `state: absent`, the playbook removes the guest and skips all provisioning, startup, and SSH wait steps.

Example removal:

```yaml
proxmox_vm:
  type: vm
  vmid: 110
  state: absent
```

For `config_change`, the playbook stores the last applied desired config fingerprint in `build/.infra-state/<inventory_hostname>.json` on the Ansible controller. This makes rebuild decisions deterministic without requiring extra metadata inside Proxmox.

## Cloud-init behavior

SSH keys from `admin_users`, and `admin_ssh_public_key` as fallback, are injected into cloud-init even when `admin_users_enabled: false`. That keeps first-login access predictable for newly created guests.

## Usage

Provision all hosts with `proxmox_vm` defined:

```bash
ansible-playbook -i inventory ansible-enterprise/build/infra.yml
```

Provision a single host:

```bash
ansible-playbook -i inventory ansible-enterprise/build/infra.yml --limit vm-example
```

Force a rebuild without changing inventory:

```bash
ansible-playbook -i inventory ansible-enterprise/build/infra.yml -e proxmox_force_rebuild=true --limit vm-example
```

`proxmox_force_rebuild=true` overrides `rebuild_on` for that run and always reprovisions the guest.

Then configure the new host with the normal site playbook:

```bash
ansible-playbook -i inventory ansible-enterprise/build/site.yml --limit vm-example
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
