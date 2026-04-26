# common

Defines the shared host-level contract: admin accounts, hostname, search domain, deployment mode, service capability map, and global toggles.

`group_vars` example:
```yaml
ssh_port: 22
admin_users:
  - name: alice
    shell: /bin/zsh
set_hostname: web01
set_domain_name: example.internal
set_domain_backend: auto
deployment_environment: production
pkg_manager_proxy:
  http_proxy: http://proxy.example.internal:3128
  https_proxy: http://proxy.example.internal:3128
  no_proxy: localhost,127.0.0.1,.example.internal
pkg_manager_update_policy: auto
pkg_manager_update_valid_time: 3600
pkg_manager_mirror:
  alpine: http://mirror.example.internal/alpine
  devuan: http://mirror.example.internal/devuan
  fedora: http://mirror.example.internal/fedora/linux

trusted_root_certificates:
  corp-root:
    pem: "{{ vault_corp_root_ca_pem }}"
  lab-root:
    src: files/lab-root-ca.crt
  existing-root:
    remote_src: /opt/ca/existing-root.pem

Debian-family hosts get a managed `/etc/apt/apt.conf.d/90ansible-enterprise-proxy`
with `Acquire::http::Proxy` / `Acquire::https::Proxy`. RedHat-family hosts get a
managed `proxy=` entry in `/etc/dnf/dnf.conf`. openSUSE hosts get a managed
`/etc/sysconfig/proxy`. Arch, Alpine, Gentoo, and FreeBSD cache refresh tasks
still receive the proxy through task environment variables.

`pkg_manager_update_policy` controls whether `site.yml` refreshes package
metadata before roles run:
- `always`: eager refresh on every run
- `auto`: use lightweight/native refresh where available (`apt` TTL); skip eager refresh on other managers
- `never`: skip eager refresh in `site.yml`

`pkg_manager_update_valid_time` is the APT TTL used in `auto` mode.

`trusted_root_certificates` installs CA roots/intermediates into the host OS
trust store. These are trust anchors for outbound TLS clients on the managed
host; they are not nginx/mailserver leaf certificates. Each entry must define
exactly one material source:

- `pem`: inline PEM content from inventory or vault
- `src`: controller-side file copied to the managed host
- `remote_src`: existing file already present on the managed host

The common role writes roots to the distro-native trust location and refreshes
the trust database:

```text
Debian/Ubuntu/Alpine/Gentoo: /usr/local/share/ca-certificates/<name>.crt
RedHat/Alma/Rocky/Fedora:   /etc/pki/ca-trust/source/anchors/<name>.crt
Arch:                       /etc/ca-certificates/trust-source/anchors/<name>.crt
openSUSE/SLES:              /etc/pki/trust/anchors/<name>.crt
FreeBSD:                    /usr/local/share/certs/<name>.pem
```

Package mirrors are rewritten during `lxc_bootstrap.yml` before Python
installation, not in `site.yml`. Supported bootstrap mirror keys currently
include `ubuntu`, `debian`, `devuan`, `alpine`, `fedora`, `rocky`, `alma`,
and `opensuse`.
```

`host_vars` example:
```yaml
set_hostname: mail01
set_domain_backend: networkmanager
firewall_enabled: true
```

`vault` example:
```yaml
admin_ssh_public_key: "ssh-ed25519 AAAA..."
admin_dev_password_hash: "$6$..."
vault_corp_root_ca_pem: |
  -----BEGIN CERTIFICATE-----
  ...
  -----END CERTIFICATE-----
```
