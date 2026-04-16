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

Debian-family hosts get a managed `/etc/apt/apt.conf.d/90ansible-enterprise-proxy`
with `Acquire::http::Proxy` / `Acquire::https::Proxy`. RedHat-family hosts get a
managed `proxy=` entry in `/etc/dnf/dnf.conf`. openSUSE hosts get a managed
`/etc/sysconfig/proxy`. Arch, Alpine, Gentoo, and FreeBSD cache refresh tasks
still receive the proxy through task environment variables.

`pkg_manager_update_policy` controls whether `site.yml` refreshes package
metadata before roles run:
- `always`: eager refresh on every run
- `auto`: use lightweight/native refresh where available (`apt` TTL, `dnf makecache --timer`)
- `never`: skip eager refresh in `site.yml`

`pkg_manager_update_valid_time` is the APT TTL used in `auto` mode.
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
```
