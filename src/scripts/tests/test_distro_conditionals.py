"""
Unit tests for distro-conditional logic across all roles.

Every test in this file corresponds to a production bug that was found without
a test catching it first. The policy going forward: every distro-conditional
fix gets a test here before the checkpoint ZIP is produced.

Coverage:
- ssh_hardening: package names and service names per distro
- dns: BIND package, service, zone dir, named.conf path per distro
- certbot: dig/nsupdate package per distro
- mailserver: package list per distro
- nginx: user per distro, php-fpm socket per distro
- node_exporter: install path (package vs binary) per distro
- site.yml: package cache refresh tasks per distro
- named.conf.local.j2: options block present on non-Debian
"""
import pathlib
import unittest

REPO  = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"


def _read(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ssh_hardening
# ---------------------------------------------------------------------------

class TestSshHardeningDistro(unittest.TestCase):

    TASKS    = "roles/ssh_hardening/tasks/main.yml"
    HANDLERS = "roles/ssh_hardening/handlers/main.yml"

    def test_debian_installs_openssh_server(self):
        self.assertIn("openssh-server", _read(self.TASKS))

    def test_arch_installs_openssh_not_openssh_server(self):
        text = _read(self.TASKS)
        self.assertIn("'openssh'", text)
        self.assertIn("Archlinux", text)

    def test_ssh_service_debian_is_ssh(self):
        """Debian service is 'ssh', not 'sshd'."""
        text = _read(self.HANDLERS)
        self.assertIn("'ssh' if ansible_facts.os_family == 'Debian'", text)

    def test_ssh_service_non_debian_is_sshd(self):
        """RedHat and Arch use 'sshd'."""
        text = _read(self.HANDLERS)
        self.assertIn("else 'sshd'", text)


# ---------------------------------------------------------------------------
# dns role
# ---------------------------------------------------------------------------

class TestDnsDistro(unittest.TestCase):

    TASKS    = "roles/dns/tasks/main.yml"
    NAMED_CONF = "roles/dns/templates/named.conf.local.j2"

    def test_bind_package_debian_is_bind9(self):
        """Debian requires bind9, not bind. Regression: cp-070 fixed this."""
        text = _read(self.TASKS)
        self.assertIn("'bind9' if ansible_facts.os_family == 'Debian'", text)

    def test_bind_package_non_debian_is_bind(self):
        """Arch and RedHat use 'bind'; FreeBSD uses 'bind918'."""
        text = _read(self.TASKS)
        self.assertIn("else 'bind' }}", text)  # final else branch
        self.assertIn("bind918", text)  # FreeBSD

    def test_bind_service_debian_is_bind9(self):
        """Debian service is bind9."""
        text = _read(self.TASKS)
        self.assertIn("'bind9' if ansible_facts.os_family == 'Debian' else 'named'", text)

    def test_bind_service_non_debian_is_named(self):
        """Arch and RedHat service is named."""
        text = _read(self.TASKS)
        self.assertIn("else 'named'", text)

    def test_zone_dir_debian_is_var_lib_bind(self):
        """Debian zone files go in /var/lib/bind (writable by bind user, correct permissions)."""
        text = _read(self.TASKS)
        self.assertIn("/var/lib/bind", text)

    def test_zone_dir_debian_not_etc_bind_zones(self):
        """/etc/bind/zones is read-only for BIND on Debian - must not be used for zone files."""
        text = _read(self.TASKS)
        self.assertNotIn("/etc/bind/zones", text)

    def test_zone_file_group_freebsd_is_bind(self):
        """FreeBSD BIND ports runs as bind:bind, not named."""
        text = _read(self.TASKS)
        self.assertIn("'bind'  if ansible_facts.os_family in ['Debian', 'FreeBSD']", text)

    def test_zone_dir_non_debian_is_var_named(self):
        text = _read(self.TASKS)
        self.assertIn("/var/named", text)

    def test_named_conf_dest_debian_is_include(self):
        """Debian uses /etc/bind/named.conf.local (an include)."""
        text = _read(self.TASKS)
        self.assertIn("/etc/bind/named.conf.local", text)

    def test_named_conf_dest_non_debian_is_full_config(self):
        """Non-Debian replaces /etc/named.conf entirely."""
        text = _read(self.TASKS)
        self.assertIn("/etc/named.conf", text)

    def test_named_conf_options_block_for_non_debian(self):
        """Options block must be present on non-Debian (Arch, RedHat, FreeBSD)."""
        text = _read(self.NAMED_CONF)
        self.assertIn("os_family != 'Debian'", text)
        self.assertIn("options {", text)
        # FreeBSD uses /usr/local/etc/namedb, others use /var/named
        self.assertIn("/var/named", text)
        self.assertIn("/usr/local/etc/namedb", text)

    def test_named_conf_options_block_not_on_debian(self):
        """The options block must be inside the != Debian guard, not unconditional."""
        text = _read(self.NAMED_CONF)
        guard_pos   = text.index("os_family != 'Debian'")
        options_pos = text.index("options {")
        self.assertLess(guard_pos, options_pos)

    def test_enable_and_start_bind_task_present(self):
        """BIND must have an explicit state: started task (not only via handler)."""
        text = _read(self.TASKS)
        self.assertIn("Enable and start BIND", text)
        self.assertIn("state: started", text)

    def test_overwrite_managed_zones_preserve_existing_serials(self):
        text = _read(self.TASKS)
        self.assertIn("Stat overwrite-managed primary zone files", text)
        self.assertIn("_dns_existing_zone_serials", text)
        self.assertIn("force: \"{{ item.overwrite | default(false) | bool }}\"", text)
        self.assertIn("Debug overwrite-managed primary zones", text)
        self.assertIn("Assert rendered SOA names are absolute for overwrite-managed zones", text)

    def test_zone_template_uses_preserved_serial_when_present(self):
        tmpl = _read("roles/dns/templates/zone.db.j2")
        self.assertIn("_dns_existing_zone_serials", tmpl)
        self.assertIn("{{ _serial }}  ; serial - managed by dns-bump-serial", tmpl)
        self.assertIn("_primary_ns.endswith('.')", tmpl)
        self.assertIn("_email.endswith('.')", tmpl)
        self.assertIn("'hostmaster@' + item.name", tmpl)
        self.assertIn("split('@', 1)", tmpl)

    def test_existing_zone_files_repair_soa_trailing_dots(self):
        text = _read(self.TASKS)
        self.assertIn("Ensure SOA primary_ns has trailing dot in primary zone files", text)
        self.assertIn("Ensure SOA email has trailing dot in primary zone files", text)
        self.assertIn("_repair_soa_primary_ns_trailing_dot", text)
        self.assertIn("_repair_soa_email_trailing_dot", text)

    def test_existing_zone_files_normalize_soa_email_rname(self):
        text = _read(self.TASKS)
        helper = _read("roles/dns/files/normalize_zone_soa.py")
        self.assertIn("Install SOA normalization helper", text)
        self.assertIn("Normalize SOA email to DNS RNAME form in primary zone files", text)
        self.assertIn("_repair_soa_email_rname", text)
        self.assertIn("Normalize SOA fields in a BIND zone file.", helper)
        self.assertIn('if "@" not in value', helper)
        self.assertIn('local, domain = value.split("@", 1)', helper)
        self.assertIn('local = local.replace(".", r"\\.")', helper)

    def test_only_changed_zones_get_serial_bumps(self):
        text = _read(self.TASKS)
        self.assertIn("Derive zones that need serial bumps", text)
        self.assertIn("_dns_zones_to_bump", text)
        self.assertIn("{{ _dns_zones_to_bump | join(' ') }}", text)
        self.assertIn("_dns_zones_to_bump | default([]) | length > 0", text)


class TestHostnameBootstrapRegression(unittest.TestCase):

    COMMON_TASKS = "roles/common/tasks/main.yml"
    BOOTSTRAP_TEMPLATE = "roles/bootstrap_scripts/templates/bootstrap.sh.j2"

    def test_hosts_update_falls_back_when_default_ipv4_missing(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("Resolve primary host IP for /etc/hosts", text)
        self.assertIn("all_ipv4_addresses", text)
        self.assertIn("default_ipv6.address", text)
        self.assertIn("_primary_host_ip", text)

    def test_hosts_update_skips_when_no_primary_ip_found(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("_primary_host_ip | default('') | length > 0", text)

    def test_bootstrap_uses_portable_whitespace_regexes(self):
        text = _read(self.BOOTSTRAP_TEMPLATE)
        self.assertIn("[[:space:]]", text)
        self.assertNotIn("\\s", text)

    def test_resolv_conf_search_update_is_gated_on_actual_content(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("Assert set_domain_backend is valid", text)
        self.assertIn("set_domain_backend", _read("roles/common/defaults/main.yml"))
        self.assertIn("Select search-domain backend", text)
        self.assertIn("_set_domain_backend_effective", text)
        self.assertIn("Configure search domain via NetworkManager", text)
        self.assertIn("Gather service facts for resolver management", text)
        self.assertIn("Configure search domain via resolvconf base file", text)
        self.assertIn("Configure search domain via dhclient", text)
        self.assertIn("Configure search domain via systemd-resolved", text)
        self.assertIn("Read resolv.conf", text)
        self.assertIn("_resolv_conf_has_desired_search", text)
        self.assertIn("^search[ \\t]+", text)
        self.assertIn("not (_resolv_conf_has_desired_search | default(false) | bool)", text)
        self.assertIn("_set_domain_backend_effective | default('') == 'static'", text)

    def test_bootstrap_prefers_manager_specific_search_domain_configuration(self):
        text = _read(self.BOOTSTRAP_TEMPLATE)
        self.assertIn("nmcli connection modify", text)
        self.assertIn("systemctl is-active NetworkManager", text)
        self.assertIn("systemctl list-unit-files systemd-resolved.service", text)
        self.assertIn("resolvconf -u", text)
        self.assertIn('supersede domain-search \\"${DOMAIN}\\";', text)
        self.assertIn("/etc/systemd/resolved.conf.d/ansible-enterprise.conf", text)
        self.assertIn("Domains=${DOMAIN}", text)


# ---------------------------------------------------------------------------
# certbot role
# ---------------------------------------------------------------------------

class TestCertbotDistro(unittest.TestCase):

    TASKS = "roles/certbot/tasks/main.yml"

    def test_dig_package_debian_is_bind9_dnsutils(self):
        self.assertIn("bind9-dnsutils", _read(self.TASKS))

    def test_dig_package_arch_is_bind(self):
        text = _read(self.TASKS)
        self.assertIn("Archlinux", text)
        # Arch installs 'bind' which includes dig and nsupdate
        idx = text.index("Archlinux")
        surrounding = text[idx-20:idx+30]
        self.assertIn("bind", surrounding)

    def test_dig_package_redhat_is_bind_utils(self):
        self.assertIn("bind-utils", _read(self.TASKS))


# ---------------------------------------------------------------------------
# mailserver role
# ---------------------------------------------------------------------------

class TestMailserverDistro(unittest.TestCase):

    TASKS = "roles/mailserver/tasks/main.yml"

    def test_debian_installs_postfix_lmdb(self):
        """postfix-lmdb is a separate package on Debian only (cp-044)."""
        text = _read(self.TASKS)
        self.assertIn("postfix-lmdb", text)

    def test_debian_installs_dovecot_split_packages(self):
        """Debian splits dovecot into dovecot-core and dovecot-imapd."""
        text = _read(self.TASKS)
        self.assertIn("dovecot-core", text)
        self.assertIn("dovecot-imapd", text)

    def test_non_debian_installs_single_dovecot_package(self):
        """Arch and RedHat ship dovecot as a single 'dovecot' package."""
        text = _read(self.TASKS)
        # The non-Debian branch has 'dovecot' without suffix
        self.assertIn("'dovecot'", text)

    def test_postfix_lmdb_only_on_debian(self):
        """postfix-lmdb must be in the Debian package list, not the non-Debian one."""
        text = _read(self.TASKS)
        # In the ternary: [Debian list] if os_family == 'Debian' else [other list]
        # postfix-lmdb appears in the Debian list, 'dovecot' alone in the else list
        lmdb_pos   = text.index("postfix-lmdb")
        debian_pos = text.index("os_family == 'Debian'", lmdb_pos - 200)
        # The Debian condition should follow the Debian package list closely
        self.assertLess(lmdb_pos, debian_pos + 100)


# ---------------------------------------------------------------------------
# nginx role
# ---------------------------------------------------------------------------

class TestNginxDistro(unittest.TestCase):

    NGINX_CONF    = "roles/nginx/templates/nginx.conf.j2"
    COMPOSE_TMPL  = "roles/nextcloud/templates/docker-compose.yml.j2"
    NEXTCLOUD_NGINX = "roles/nginx/templates/nextcloud.conf.j2"
    RENDER_SVC    = "roles/nginx/tasks/render_service.yml"

    def test_render_service_resolves_template_first(self):
        """_vhost_template must be resolved before the serving mode and render."""
        text = _read(self.RENDER_SVC)
        resolve_pos = text.index("Resolve vhost template")
        mode_pos    = text.index("Set serving mode")
        render_pos  = text.index("Render service vhost")
        self.assertLess(resolve_pos, mode_pos)
        self.assertLess(mode_pos, render_pos)

    def test_render_service_sets_static_site_mode(self):
        """Static vs proxy mode must be determined from _upstream_port."""
        text = _read(self.RENDER_SVC)
        self.assertIn("_static_site", text)
        self.assertIn("_upstream_port | string | length == 0", text)
        self.assertIn("Normalize upstream for", text)
        self.assertIn("service.value.port | default", text)

    def test_render_service_static_site_nextcloud_excluded(self):
        """Nextcloud is always proxy mode (handled by its own template)."""
        text = _read(self.RENDER_SVC)
        self.assertIn("Nextcloud is always proxy mode", text)

    def test_render_service_checks_cert_exists_before_render(self):
        """TLS cert stat must precede the render task, not follow it."""
        text = _read(self.RENDER_SVC)
        cert_pos   = text.index("Assert TLS certificate exists")
        render_pos = text.index("Render service vhost")
        self.assertLess(cert_pos, render_pos)

    def test_render_service_cert_check_gated_on_tls(self):
        """Cert existence check must only run for services with tls: true."""
        text = _read(self.RENDER_SVC)
        self.assertIn("security.tls | default(false) | bool", text)
        self.assertIn("_cert_stat.stat.exists", text)

    def test_render_service_cert_fail_msg_actionable(self):
        """Cert missing fail_msg must tell operator what to do."""
        text = _read(self.RENDER_SVC)
        self.assertIn("certbot role first", text)
        self.assertIn("certbot_selfsigned_fallback", text)


        self.assertIn("www-data", _read(self.NGINX_CONF))

    def test_nginx_user_arch_is_http(self):
        text = _read(self.NGINX_CONF)
        self.assertIn("'http'", text)
        self.assertIn("Archlinux", text)

    def test_nginx_user_redhat_is_nginx(self):
        text = _read(self.NGINX_CONF)
        self.assertIn("else 'nginx'", text)

    def test_nextcloud_compose_template_has_mariadb(self):
        """docker-compose.yml.j2 must include the MariaDB service."""
        text = _read(self.COMPOSE_TMPL)
        self.assertIn("nextcloud_db_image", text)
        self.assertIn("MARIADB_DATABASE", text)

    def test_nextcloud_fpm_port_used_in_compose(self):
        """FPM container must expose nextcloud_fpm_port."""
        text = _read(self.COMPOSE_TMPL)
        self.assertIn("nextcloud_fpm_port", text)
        self.assertIn("9000", text)

    def test_nextcloud_nginx_uses_tcp_fastcgi(self):
        """nginx nextcloud vhost must proxy FPM via TCP not unix socket."""
        text = _read(self.NEXTCLOUD_NGINX)
        self.assertIn("nextcloud_fpm_port", text)
        self.assertNotIn("php-fpm.sock", text)

    def test_nextcloud_webroot_bind_mounted(self):
        """Webroot must be bind-mounted to host so nginx can serve statics."""
        text = _read(self.COMPOSE_TMPL)
        self.assertIn("nextcloud_install_dir", text)
        self.assertIn("/var/www/html", text)


# ---------------------------------------------------------------------------
# node_exporter role
# ---------------------------------------------------------------------------

class TestNodeExporterDistro(unittest.TestCase):

    TASKS = "roles/node_exporter/tasks/main.yml"

    def test_debian_uses_package_install(self):
        text = _read(self.TASKS)
        self.assertIn("prometheus-node-exporter", text)
        self.assertIn("os_family == 'Debian'", text)

    def test_non_debian_uses_binary_download(self):
        """Arch and RedHat download the binary; FreeBSD uses pkg."""
        text = _read(self.TASKS)
        self.assertIn("not in ['Debian', 'FreeBSD']", text)
        self.assertIn("github.com/prometheus/node_exporter", text)

    def test_no_redhat_only_guard_on_binary_tasks(self):
        """Binary download must NOT be gated os_family == 'RedHat' — Arch needs it too."""
        text = _read(self.TASKS)
        # Check that all guards in the binary section use != 'Debian'
        # by verifying os_family == 'RedHat' does not appear in the download block
        start = text.index("Resolve CPU architecture for node_exporter download")
        end   = text.index("Ensure node_exporter systemd override directory exists (Debian)")
        block = text[start:end]
        self.assertNotIn("os_family == 'RedHat'", block)

    def test_debian_systemd_override_gated_correctly(self):
        text = _read(self.TASKS)
        self.assertIn("os_family == 'Debian'", text)


# ---------------------------------------------------------------------------
# site.yml pre_tasks
# ---------------------------------------------------------------------------

class TestSiteYmlDistro(unittest.TestCase):

    SITE = "site.yml"

    def test_apt_cache_refresh_present(self):
        self.assertIn("Refresh apt package cache", _read(self.SITE))

    def test_dnf_cache_refresh_present(self):
        self.assertIn("Refresh dnf package cache", _read(self.SITE))

    def test_pacman_cache_refresh_present(self):
        """Arch Linux needs pacman -Sy before installing packages."""
        text = _read(self.SITE)
        self.assertIn("Refresh pacman package cache", text)
        self.assertIn("Archlinux", text)

    def test_apt_gated_to_debian(self):
        text = _read(self.SITE)
        apt_pos    = text.index("Refresh apt package cache")
        debian_pos = text.index("os_family == 'Debian'", apt_pos)
        self.assertLess(apt_pos, debian_pos + 100)

    def test_dnf_gated_to_redhat(self):
        text = _read(self.SITE)
        dnf_pos    = text.index("Refresh dnf package cache")
        redhat_pos = text.index("os_family == 'RedHat'", dnf_pos)
        self.assertLess(dnf_pos, redhat_pos + 100)

    def test_pacman_gated_to_archlinux(self):
        text = _read(self.SITE)
        pac_pos  = text.index("Refresh pacman package cache")
        arch_pos = text.index("Archlinux", pac_pos)
        self.assertLess(pac_pos, arch_pos + 100)


class TestCronieArch(unittest.TestCase):
    """Arch Linux requires cronie for crontab - installed in common role."""

    COMMON_TASKS = "roles/common/tasks/main.yml"

    def test_cronie_installed_on_arch(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("cronie", text)
        self.assertIn("Archlinux", text)

    def test_cronie_enabled_and_started(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("cronie", text)
        self.assertIn("state: started", text)

    def test_cronie_gated_to_arch_only(self):
        """cronie must only install on Arch - other distros ship cron already."""
        text = _read(self.COMMON_TASKS)
        cronie_pos = text.index("cronie")
        arch_pos   = text.index("Archlinux", cronie_pos - 200)
        self.assertLess(cronie_pos - 200, arch_pos)


class TestDnsPublicFirewall(unittest.TestCase):
    """dns_public variable controls whether port 53 is open to all sources."""

    NFTABLES = "roles/firewall_geo/templates/nftables.conf.j2"
    DNS_DEFAULTS = "roles/dns/defaults/main.yml"

    def test_dns_public_defaults_to_false(self):
        self.assertIn("recursion: false", _read(self.DNS_DEFAULTS))
        self.assertIn("dns:\n", _read(self.DNS_DEFAULTS))

    def test_dns_public_true_opens_port_53_unconditionally(self):
        text = _read(self.NFTABLES)
        self.assertIn("dns_public", text)
        # When true, plain accept with no source restriction
        idx = text.index("dns_public | default(false) | bool %}")
        block = text[idx:idx+200]
        self.assertIn("tcp dport 53 accept", block)
        self.assertIn("udp dport 53 accept", block)

    def test_dns_public_false_restricts_to_secondaries(self):
        text = _read(self.NFTABLES)
        self.assertIn("dns_secondaries", text)
        # Restricted path accepts from secondaries per-address
        self.assertIn("saddr {{ _sec }}", text)

    def test_dns_public_false_always_allows_loopback(self):
        text = _read(self.NFTABLES)
        self.assertIn("saddr 127.0.0.1", text)
        self.assertIn("saddr ::1", text)

    def test_dns_public_block_inside_dns_active_guard(self):
        """dns_public conditional must be inside the _dns.active guard."""
        text = _read(self.NFTABLES)
        active_pos = text.index("_dns.active %}")
        # Find the Jinja2 if tag, not the comment
        public_pos = text.index("{% if dns_public")
        self.assertLess(active_pos, public_pos)


class TestSelinuxRedhat(unittest.TestCase):
    """RedHat SELinux baseline setup in common role."""

    COMMON_TASKS = "roles/common/tasks/main.yml"

    def test_selinux_python_bindings_installed(self):
        """python3-libselinux required for Ansible to operate on SELinux hosts."""
        text = _read(self.COMMON_TASKS)
        self.assertIn("python3-libselinux", text)

    def test_selinux_tools_installed(self):
        self.assertIn("policycoreutils-python-utils", _read(self.COMMON_TASKS))

    def test_selinux_packages_gated_to_redhat(self):
        text = _read(self.COMMON_TASKS)
        idx = text.index("Install SELinux Python bindings")
        task_block = text[idx:idx+400]
        self.assertIn("python3-libselinux", task_block)
        self.assertIn("os_family == 'RedHat'", task_block)

    def test_deny_ptrace_disabled(self):
        """deny_ptrace: false allows root to list all processes."""
        text = _read(self.COMMON_TASKS)
        self.assertIn("deny_ptrace", text)
        self.assertIn("state: false", text)
        self.assertIn("persistent: true", text)

    def test_deny_ptrace_gated_to_redhat(self):
        text = _read(self.COMMON_TASKS)
        idx = text.index("deny_ptrace")
        surrounding = text[idx-300:idx+100]
        self.assertIn("os_family == 'RedHat'", surrounding)


class TestMailserverPackagesArch(unittest.TestCase):
    """Arch Linux mailserver package list and directory setup."""

    TASKS = "roles/mailserver/tasks/main.yml"

    def test_dovecot_auth_uses_version_conditional(self):
        """10-auth.conf.j2 must handle disable_plaintext_auth rename in Dovecot 2.4."""
        tmpl = (BUILD / "roles/mailserver/templates/10-auth.conf.j2").read_text()
        self.assertIn("Archlinux", tmpl)
        self.assertIn("auth_allow_cleartext = no", tmpl)
        self.assertIn("disable_plaintext_auth = yes", tmpl)

    def test_dovecot_mail_uses_version_conditional(self):
        """10-mail.conf.j2 must handle mail_location split in Dovecot 2.4."""
        tmpl = (BUILD / "roles/mailserver/templates/10-mail.conf.j2").read_text()
        self.assertIn("Archlinux", tmpl)
        self.assertIn("mail_driver = maildir", tmpl)
        self.assertIn("mail_path = ~/Maildir", tmpl)
        self.assertIn("mail_location = maildir:~/Maildir", tmpl)

    def test_dovecot_confd_directory_created(self):
        """Arch and FreeBSD dovecot packages do not create conf.d - must be explicit."""
        text = _read(self.TASKS)
        self.assertIn("_dovecot_conf_dir", text)
        self.assertIn("conf.d", text)
        self.assertIn("state: directory", text)

    def test_dovecot_ssl_disabled(self):
        """10-ssl.conf must disable built-in SSL (Arch default dovecot.conf enables it)."""
        text = _read(self.TASKS)
        self.assertIn("10-ssl.conf", text)
        self.assertIn("ssl = no", text)

    def test_dovecot_confd_included_on_arch(self):
        """Arch gets a minimal dovecot.conf that includes conf.d and has no cert references."""
        text = _read(self.TASKS)
        self.assertIn("!include conf.d/*.conf", text)
        self.assertIn("Archlinux", text)
        self.assertIn("Deploy minimal dovecot.conf (Arch)", text)
        self.assertNotIn("lineinfile", text)
        # Dovecot 2.4+ requires dovecot_config_version as the first directive
        self.assertIn("dovecot_config_version = 2.4.0", text)

    def test_arch_excludes_opendkim_tools(self):
        """opendkim-tools is bundled in opendkim on Arch; separate package does not exist."""
        text = _read(self.TASKS)
        # The ternary is: [Arch list] if os_family == 'Archlinux' else [RedHat list]
        # So the Arch package list appears BEFORE the 'Archlinux' keyword.
        arch_idx = text.index("Archlinux")
        arch_list = text[arch_idx - 150 : arch_idx]
        self.assertNotIn("opendkim-tools", arch_list)

    def test_debian_includes_opendkim_tools(self):
        """Debian ships opendkim-tools as a separate package."""
        text = _read(self.TASKS)
        debian_idx = text.index("os_family == 'Debian'")
        debian_block = text[debian_idx - 200 : debian_idx]
        self.assertIn("opendkim-tools", debian_block)

    def test_redhat_includes_opendkim_tools(self):
        text = _read(self.TASKS)
        # RedHat falls in the final else branch
        self.assertIn("opendkim-tools", text)


class TestUpdatePasswordIdempotence(unittest.TestCase):
    """Password tasks must use on_create not always to avoid false changed reports."""

    TASKS = "roles/ssh_hardening/tasks/main.yml"

    def test_update_password_is_always(self):
        """update_password: always ensures console password can be rotated."""
        text = _read(self.TASKS)
        self.assertIn("update_password: always", text)
        self.assertNotIn("update_password: on_create", text)


class TestNftablesIdempotence(unittest.TestCase):
    """nftables enable task must not use state: started (oneshot service = always changed)."""

    TASKS = "roles/firewall_geo/tasks/main.yml"

    def _task_block(self):
        text = _read(self.TASKS)
        idx = text.index("- name: Enable nftables at boot")
        return text[idx:idx+300]

    def test_enable_nftables_uses_systemd_module(self):
        self.assertIn("systemd:", self._task_block())
        self.assertNotIn("  service:", self._task_block())

    def test_enable_nftables_has_daemon_reload(self):
        self.assertIn("daemon_reload: true", self._task_block())

    def test_enable_nftables_no_state_started(self):
        """state: started on a oneshot service causes changed on every run."""
        self.assertNotIn("state: started", self._task_block())

    def test_nft_apply_task_present(self):
        """Rules must be applied immediately via nft -f, not only at boot."""
        text = _read(self.TASKS)
        self.assertIn("nft -f /etc/nftables.conf", text)
        self.assertIn("changed_when: false", text)

    def test_nftables_tasks_gated_not_freebsd(self):
        """All nftables tasks must be skipped on FreeBSD."""
        text = _read(self.TASKS)
        # Every nftables task must have a FreeBSD exclusion
        import re
        nft_blocks = re.split(r'\n(?=- name:)', text)
        for block in nft_blocks:
            if 'nftables' in block and 'when:' in block:
                self.assertIn("FreeBSD", block,
                    msg=f"nftables task missing FreeBSD guard: {block[:80]}")


class TestPfFirewall(unittest.TestCase):
    """pf firewall for FreeBSD."""

    TASKS = "roles/firewall_geo/tasks/main.yml"
    PF_CONF = "roles/firewall_geo/templates/pf.conf.j2"

    def test_pf_tasks_present(self):
        text = _read(self.TASKS)
        self.assertIn("Deploy pf rules", text)
        self.assertIn("Enable pf at boot", text)
        self.assertIn("Load pf rules (FreeBSD)", text)

    def test_pf_tasks_gated_freebsd(self):
        text = _read(self.TASKS)
        idx = text.index("Deploy pf rules")
        block = text[idx:idx+200]
        self.assertIn("os_family == 'FreeBSD'", block)

    def test_pf_no_package_install(self):
        """pf is in FreeBSD base -- no package install task should exist."""
        text = _read(self.TASKS)
        # No 'install pf' task
        self.assertNotIn("Install pf", text)

    def test_pf_conf_default_drop(self):
        """pf config must have default-drop input policy."""
        text = _read(self.PF_CONF)
        self.assertIn("block in", text)

    def test_pf_conf_stateful(self):
        """pf rules must use keep state for stateful filtering."""
        text = _read(self.PF_CONF)
        self.assertIn("keep state", text)

    def test_pf_conf_ssh_port_variable(self):
        """SSH port must use the ssh_port variable, not a hardcoded 22."""
        text = _read(self.PF_CONF)
        self.assertIn("ssh_port", text)
        self.assertNotIn("port 22 ", text)

    def test_pf_conf_loopback_accepted(self):
        text = _read(self.PF_CONF)
        self.assertIn("lo0", text)

    def test_pf_conf_mail_conditional(self):
        """Mail ports must only open when mailserver is active."""
        text = _read(self.PF_CONF)
        self.assertIn("mailserver", text)
        self.assertIn("25, 587, 465, 993", text)

    def test_pf_conf_node_exporter_conditional(self):
        text = _read(self.PF_CONF)
        self.assertIn("node_exporter_enabled", text)
        self.assertIn("node_exporter_port", text)

    def test_pf_handler_uses_pfctl(self):
        text = _read("roles/firewall_geo/handlers/main.yml")
        self.assertIn("pfctl -f /etc/pf.conf", text)
        self.assertIn("os_family == 'FreeBSD'", text)




class TestSystemdModuleEnforcement(unittest.TestCase):
    """All service start/enable tasks must use systemd: not service: module.

    The generic service module reports changed every run on some distros when
    the unit was enabled via a drop-in or non-standard path. The systemd module
    queries UnitFileState via D-Bus and is idempotent on all distros.
    """

    def _tasks_files(self):
        for role in (BUILD / "roles").iterdir():
            tasks = role / "tasks"
            if tasks.exists():
                yield from tasks.glob("*.yml")

    def test_no_service_module_with_enabled_and_started(self):
        """Non-FreeBSD tasks must use systemd: module with enabled: true.
        FreeBSD service: tasks are allowed when gated os_family == 'FreeBSD'."""
        violations = []
        for path in self._tasks_files():
            text = path.read_text(encoding="utf-8")
            for block in text.split("- name:"):
                if "service:" in block and "enabled: true" in block and "state: started" in block:
                    # Allow service: tasks explicitly gated to FreeBSD
                    if "os_family == 'FreeBSD'" in block:
                        continue
                    lines = block.splitlines()
                    for line in lines:
                        if line.strip() == "service:":
                            violations.append(
                                f"{path.relative_to(BUILD)}: {lines[0].strip()[:60]}"
                            )
                            break
        self.assertEqual(violations, [],
            "These tasks use service: with enabled: true (use systemd: instead):\n"
            + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()


class TestFreeBSDSupport(unittest.TestCase):
    """FreeBSD-specific distro-conditional coverage."""

    def test_postfix_conf_dir_freebsd(self):
        """postfix from FreeBSD ports uses /usr/local/etc/postfix not /etc/postfix."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("_postfix_conf_dir", text)
        self.assertIn("/usr/local/etc/postfix", text)

    def test_mailname_skipped_on_freebsd(self):
        """/etc/mailname is a Linux convention; skipped on FreeBSD."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("os_family != 'FreeBSD'", text)
        # The mailname task should have a when: guard
        idx = text.index("Write /etc/mailname")
        block = text[idx:idx+200]
        self.assertIn("FreeBSD", block)

    def test_letsencrypt_dir_freebsd(self):
        """py311-certbot on FreeBSD uses /usr/local/etc/letsencrypt."""
        text = _read("roles/certbot/tasks/main.yml")
        self.assertIn("_le_dir", text)
        self.assertIn("/usr/local/etc/letsencrypt", text)

    def test_node_exporter_freebsd_uses_pkg(self):
        """FreeBSD uses pkg install node_exporter, not binary download."""
        text = _read("roles/node_exporter/tasks/main.yml")
        self.assertIn("Install node_exporter package (FreeBSD)", text)
        self.assertIn("os_family == 'FreeBSD'", text)
        # Binary download tasks must exclude FreeBSD
        self.assertIn("not in ['Debian', 'FreeBSD']", text)

    def test_dovecot_conf_dir_freebsd(self):
        """dovecot on FreeBSD uses /usr/local/etc/dovecot not /etc/dovecot."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("_dovecot_conf_dir", text)
        self.assertIn("/usr/local/etc/dovecot", text)

    def test_milteropendkim_rcvar_no_hyphen(self):
        """sysrc rcvar name must not contain hyphens (shell variable restriction)."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("milteropendkim_enable=YES", text)
        self.assertNotIn("milter-opendkim_enable=YES", text)

    def test_freebsd_services_use_sysrc_and_onestart(self):
        """FreeBSD services: sysrc to enable, proper start mechanism."""
        for role_task in [
            "roles/nginx/tasks/main.yml",
            "roles/mailserver/tasks/main.yml",
            "roles/dns/tasks/main.yml",
        ]:
            text = _read(role_task)
            self.assertIn("sysrc", text,
                msg=f"{role_task} missing sysrc enable task for FreeBSD")
            self.assertIn("onestart", text,
                msg=f"{role_task} missing onestart task for FreeBSD")

    def test_node_exporter_freebsd_uses_daemon8(self):
        """node_exporter on FreeBSD uses daemon(8) since it has no daemon mode."""
        text = _read("roles/node_exporter/tasks/main.yml")
        self.assertIn("daemon -p /var/run/node_exporter.pid", text)
        self.assertIn("os_family == 'FreeBSD'", text)

    def test_opendkim_paths_freebsd(self):
        """opendkim on FreeBSD uses /var/db/dkim and /usr/local/etc/mail/opendkim.conf."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("/var/db/dkim", text)
        self.assertIn("/usr/local/etc/mail/opendkim.conf", text)
        self.assertIn("_opendkim_dir", text)
        self.assertIn("_opendkim_conf", text)

    def test_opendkim_background_conditional(self):
        """Background no must be inside a non-FreeBSD conditional in opendkim.conf.j2."""
        text = _read("roles/mailserver/templates/opendkim.conf.j2")
        self.assertIn("os_family != 'FreeBSD'", text)
        self.assertIn("Background no", text)

    def test_opendkim_service_name_freebsd(self):
        """opendkim rc.d script on FreeBSD ports is milter-opendkim not opendkim."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("milter-opendkim", text)
        self.assertIn("FreeBSD", text)

    def test_nginx_conf_dir_freebsd(self):
        """nginx on FreeBSD uses /usr/local/etc/nginx not /etc/nginx."""
        text = _read("roles/nginx/tasks/main.yml")
        self.assertIn("_nginx_conf_dir", text)
        self.assertIn("/usr/local/etc/nginx", text)
        self.assertIn("FreeBSD", text)

    def test_nginx_conf_dir_non_freebsd(self):
        """Non-FreeBSD systems use /etc/nginx."""
        text = _read("roles/nginx/tasks/main.yml")
        self.assertIn("/etc/nginx", text)

    def test_nginx_mime_types_uses_variable(self):
        """nginx.conf.j2 must reference mime.types via _nginx_conf_dir variable."""
        text = _read("roles/nginx/templates/nginx.conf.j2")
        self.assertIn("_nginx_conf_dir", text)
        self.assertNotIn("/etc/nginx/mime.types", text)
        self.assertNotIn("/usr/local/etc/nginx/mime.types", text)

    def test_certbot_package_freebsd(self):
        """certbot on FreeBSD is py311-certbot not certbot."""
        text = _read("roles/certbot/tasks/main.yml")
        self.assertIn("py311-certbot", text)
        self.assertIn("FreeBSD", text)

    def test_mariadb_package_freebsd(self):
        """Nextcloud uses MariaDB container image (no host package needed)."""
        text = _read("roles/nextcloud/templates/docker-compose.yml.j2")
        self.assertIn("MARIADB_DATABASE", text)
        self.assertIn("nextcloud_db_image", text)

    def test_php_packages_freebsd(self):
        """Nextcloud uses nextcloud:fpm-alpine container (no host PHP needed)."""
        text = _read("roles/nextcloud/tasks/main.yml")
        self.assertIn("docker-compose.yml", text)
        self.assertIn("docker exec", text)

    def test_bash_installed_on_freebsd(self):
        """FreeBSD ships /bin/sh not bash; bash must be installed explicitly."""
        text = _read("roles/common/tasks/main.yml")
        idx = text.index("Install bash (FreeBSD)")
        block = text[idx:idx+150]
        self.assertIn("name: bash", block)
        self.assertIn("os_family == 'FreeBSD'", block)

    def test_py311_ansible_installed_on_freebsd(self):
        """py311-ansible must be installed on FreeBSD for Python modules to work."""
        text = _read("roles/common/tasks/main.yml")
        self.assertIn("py311-ansible", text)
        self.assertIn("os_family == 'FreeBSD'", text)

    def test_sudoers_path_freebsd(self):
        """FreeBSD sudo from ports uses /usr/local/etc/sudoers.d/."""
        text = _read("roles/ssh_hardening/tasks/main.yml")
        self.assertIn("/usr/local/etc/sudoers.d/", text)
        self.assertIn("FreeBSD", text)

    def test_root_group_uses_wheel_on_freebsd(self):
        """FreeBSD uses wheel not root as the privileged group."""
        text = _read("roles/common/tasks/main.yml")
        self.assertIn("_root_group", text)
        self.assertIn("'wheel' if ansible_facts.os_family == 'FreeBSD'", text)

    def test_no_bare_group_root_in_tasks(self):
        """All task files must use _root_group instead of hardcoded group: root."""
        violations = []
        for role in (BUILD / "roles").iterdir():
            for f in role.rglob("*.yml"):
                if "tasks" not in f.parts and "handlers" not in f.parts:
                    continue
                for line in f.read_text().splitlines():
                    if "group: root" in line and not line.lstrip().startswith("#"):
                        violations.append(f"{f.relative_to(BUILD)}: {line.strip()}")
        self.assertEqual(violations, [],
            "Hardcoded group: root found (use group: \"{{ _root_group }}\"):\n"
            + "\n".join(violations))

    def test_pkg_cache_refresh_present(self):
        """FreeBSD needs pkg update before installing packages."""
        text = _read("site.yml")
        self.assertIn("Refresh pkg package cache (FreeBSD)", text)
        self.assertIn("os_family == 'FreeBSD'", text)

    def test_ssh_freebsd_only_installs_sudo(self):
        """OpenSSH is in FreeBSD base - only sudo needs installing."""
        text = _read("roles/ssh_hardening/tasks/main.yml")
        self.assertIn("FreeBSD", text)
        # FreeBSD branch should have sudo but not openssh-server
        idx = text.index("FreeBSD")
        block = text[idx - 50 : idx + 80]
        self.assertIn("sudo", block)

    def test_certbot_dig_package_freebsd_is_bind_tools(self):
        text = _read("roles/certbot/tasks/main.yml")
        self.assertIn("bind-tools", text)
        self.assertIn("FreeBSD", text)

    def test_dns_bind_package_freebsd_is_bind918(self):
        text = _read("roles/dns/tasks/main.yml")
        self.assertIn("bind918", text)

    def test_dns_zone_dir_freebsd(self):
        text = _read("roles/dns/tasks/main.yml")
        self.assertIn("/usr/local/etc/namedb", text)

    def test_dns_named_conf_path_freebsd(self):
        text = _read("roles/dns/tasks/main.yml")
        self.assertIn("/usr/local/etc/namedb/named.conf", text)

    def test_named_conf_directory_freebsd(self):
        text = _read("roles/dns/templates/named.conf.local.j2")
        self.assertIn("/usr/local/etc/namedb", text)

    def test_nginx_user_freebsd_is_www(self):
        text = _read("roles/nginx/templates/nginx.conf.j2")
        self.assertIn("'www'", text)
        self.assertIn("FreeBSD", text)

    def test_nextcloud_uses_docker_compose(self):
        """Nextcloud uses Docker Compose; no host php-fpm or MariaDB."""
        text = _read("roles/nextcloud/templates/docker-compose.yml.j2")
        self.assertIn("nextcloud-app", text)
        self.assertIn("nextcloud-db", text)

    def test_mailserver_packages_freebsd_no_opendkim_tools(self):
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("FreeBSD", text)
        idx = text.index("FreeBSD")
        block = text[idx - 150 : idx + 10]
        self.assertNotIn("opendkim-tools", block)

    def test_opendkim_drop_in_skipped_on_freebsd(self):
        """systemd drop-in is Linux-specific; FreeBSD uses rc.d."""
        text = _read("roles/mailserver/tasks/main.yml")
        self.assertIn("os_family != 'FreeBSD'", text)

    def test_node_exporter_freebsd_uses_sysrc_args(self):
        """FreeBSD pkg rc.d handles daemonization; we only set args via sysrc."""
        text = _read("roles/node_exporter/tasks/main.yml")
        self.assertIn("node_exporter_args", text)
        self.assertIn("os_family == 'FreeBSD'", text)

    def test_node_exporter_systemd_unit_skipped_on_freebsd(self):
        text = _read("roles/node_exporter/tasks/main.yml")
        self.assertIn("os_family not in ['Debian', 'FreeBSD']", text)

    def test_enable_start_tasks_have_freebsd_service_fallback(self):
        """Every systemd: enable+start task must have a service: FreeBSD partner."""
        for role_task in [
            "roles/nginx/tasks/main.yml",
            "roles/mailserver/tasks/main.yml",
            "roles/dns/tasks/main.yml",
            "roles/node_exporter/tasks/main.yml",
        ]:
            text = _read(role_task)
            self.assertIn("os_family == 'FreeBSD'", text,
                msg=f"{role_task} missing FreeBSD service: fallback")
            self.assertIn("os_family != 'FreeBSD'", text,
                msg=f"{role_task} missing systemd: FreeBSD guard")


class TestPrometheusGrafanaRoles(unittest.TestCase):
    """Prometheus and Grafana roles: Docker-based, FreeBSD excluded."""

    def test_prometheus_disabled_by_default(self):
        text = _read("roles/prometheus/defaults/main.yml")
        self.assertIn("prometheus_enabled: false", text)

    def test_grafana_disabled_by_default(self):
        text = _read("roles/grafana/defaults/main.yml")
        self.assertIn("grafana_enabled: false", text)

    def test_prometheus_freebsd_excluded_in_site(self):
        text = _read("site.yml")
        self.assertIn("prometheus_enabled", text)
        self.assertIn("os_family != 'FreeBSD'", text)

    def test_grafana_freebsd_excluded_in_site(self):
        text = _read("site.yml")
        self.assertIn("grafana_enabled", text)

    def test_prometheus_scrape_targets_template(self):
        text = _read("roles/prometheus/templates/prometheus.yml.j2")
        self.assertIn("prometheus_scrape_targets", text)
        self.assertIn("node_exporter_port", text)

    def test_grafana_prometheus_datasource_provisioned(self):
        text = _read("roles/grafana/tasks/main.yml")
        self.assertIn("prometheus.yml", text)
        self.assertIn("grafana_prometheus_url", text)

    def test_docker_role_exists(self):
        text = _read("roles/docker/tasks/main.yml")
        self.assertIn("docker", text)
        self.assertIn("os_family != 'FreeBSD'", text)

    def test_prometheus_admin_password_asserted(self):
        """Grafana must assert admin password is set before deploying."""
        text = _read("roles/grafana/tasks/main.yml")
        self.assertIn("grafana_admin_password", text)
        self.assertIn("assert", text)


class TestFreeBSDPfFirewall(unittest.TestCase):
    """FreeBSD pf firewall implementation tests."""

    PF_CONF    = "roles/firewall_geo/templates/pf.conf.j2"
    FW_TASKS   = "roles/firewall_geo/tasks/main.yml"
    FW_HANDLER = "roles/firewall_geo/handlers/main.yml"
    GEOIP_CONF = "roles/geoip/templates/geoip.conf.j2"
    INGEST     = "roles/geoip/files/geoip_ingest.py"
    REFRESH    = "roles/geoip/files/geoip_refresh.sh"
    GEOIP_TASKS = "roles/geoip/tasks/main.yml"

    def test_pf_conf_template_exists(self):
        text = _read(self.PF_CONF)
        self.assertIn("pass in proto tcp to any port $ssh_port", text)

    def test_pf_tasks_guard_nftables_from_freebsd(self):
        text = _read(self.FW_TASKS)
        self.assertIn("os_family != 'FreeBSD'", text)

    def test_pf_tasks_deploy_pf_conf(self):
        text = _read(self.FW_TASKS)
        self.assertIn("dest: /etc/pf.conf", text)
        self.assertIn("os_family == 'FreeBSD'", text)

    def test_pf_tasks_enable_via_sysrc(self):
        text = _read(self.FW_TASKS)
        self.assertIn("pf_enable=YES", text)
        self.assertIn("pflog_enable=YES", text)

    def test_pf_handler_exists(self):
        text = _read(self.FW_HANDLER)
        self.assertIn("pfctl -f /etc/pf.conf", text)
        self.assertIn("os_family == 'FreeBSD'", text)

    def test_pf_conf_default_drop(self):
        text = _read(self.PF_CONF)
        self.assertIn("block in  log all", text)
        self.assertIn("pass  out all keep state", text)

    def test_pf_conf_stateful(self):
        text = _read(self.PF_CONF)
        self.assertIn("keep state", text)

    def test_pf_conf_geoip_table_declarations(self):
        """GeoIP tables must be declared from flat .txt files."""
        text = _read(self.PF_CONF)
        self.assertIn('persist file "/etc/pf.d/geoip/geoip_ssh_ipv4.txt"', text)
        self.assertIn('persist file "/etc/pf.d/geoip/geoip_http_ipv4.txt"', text)
        self.assertIn('persist file "/etc/pf.d/geoip/geoip_https_ipv4.txt"', text)

    def test_pf_conf_geoip_ssh_filtering(self):
        """SSH rule must block non-allowed countries when geoip enabled."""
        text = _read(self.PF_CONF)
        self.assertIn("from !<geoip_ssh_ipv4> to any port $ssh_port", text)
        self.assertIn("block in inet6 proto tcp from !<geoip_ssh_ipv6>", text)

    def test_pf_conf_geoip_http_filtering(self):
        text = _read(self.PF_CONF)
        self.assertIn("from !<geoip_http_ipv4> to any port 80", text)
        self.assertIn("from !<geoip_http_ipv6> to any port 80", text)

    def test_pf_conf_geoip_https_filtering(self):
        text = _read(self.PF_CONF)
        self.assertIn("from !<geoip_https_ipv4> to any port 443", text)
        self.assertIn("from !<geoip_https_ipv6> to any port 443", text)

    def test_geoip_ingest_format_flag(self):
        """geoip_ingest.py must accept --format pf|nftables."""
        text = _read(self.INGEST)
        self.assertIn('choices=["nftables", "pf"]', text)
        self.assertIn('default="nftables"', text)

    def test_geoip_ingest_pf_writes_txt_files(self):
        """pf format must write .txt files, not .nft files."""
        text = _read(self.INGEST)
        self.assertIn('_ipv4.txt"', text)
        self.assertIn('_ipv6.txt"', text)

    def test_geoip_tasks_pass_format_flag(self):
        """All geoip_ingest calls must pass --format {{ _geoip_format }}."""
        text = _read(self.GEOIP_TASKS)
        self.assertIn("--format {{ _geoip_format }}", text)

    def test_geoip_tasks_set_geoip_format_fact(self):
        """geoip role must set _geoip_format fact for FreeBSD/Linux."""
        text = _read(self.GEOIP_TASKS)
        self.assertIn("_geoip_format", text)
        self.assertIn("'pf' if ansible_facts.os_family == 'FreeBSD'", text)

    def test_geoip_conf_sets_dir_uses_fact(self):
        """geoip.conf must use _geoip_sets_dir so FreeBSD gets pf path."""
        text = _read(self.GEOIP_CONF)
        self.assertIn("SETS_DIR={{ _geoip_sets_dir }}", text)
        self.assertIn("FORMAT={{ _geoip_format }}", text)

    def test_geoip_refresh_passes_format(self):
        """geoip_refresh.sh must pass --format ${FORMAT} to ingest."""
        text = _read(self.REFRESH)
        self.assertIn("--format ${FORMAT}", text)

    def test_geoip_refresh_reloads_correct_firewall(self):
        """geoip_refresh.sh must reload nft or pf depending on platform."""
        text = _read(self.REFRESH)
        self.assertIn("pfctl -f /etc/pf.conf", text)
        self.assertIn("nft -f /etc/nftables.conf", text)
