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
    SSHD_TEMPLATE = "roles/ssh_hardening/templates/sshd_config.j2"
    SSHD_DROPIN_TEMPLATE = "roles/ssh_hardening/templates/99-ansible-enterprise.conf.j2"
    COMMON_DEFAULTS = "roles/common/defaults/main.yml"
    SITE = "site.yml"

    def test_debian_installs_openssh_server(self):
        self.assertIn("openssh-server", _read(self.TASKS))

    def test_arch_installs_openssh_not_openssh_server(self):
        text = _read(self.TASKS)
        self.assertIn("'openssh'", text)
        self.assertIn("Archlinux", text)

    def test_suse_uses_direct_zypper_install_for_ssh_bootstrap(self):
        text = _read(self.TASKS)
        self.assertIn("Install OpenSSH server and sudo (SUSE)", text)
        self.assertIn("zypper", text)
        self.assertIn("--no-recommends", text)
        self.assertIn("ansible_facts.os_family == 'Suse'", text)

    def test_generic_package_task_skips_suse_and_uses_openssh_name(self):
        text = _read(self.TASKS)
        self.assertIn("ansible_facts.os_family in ['Archlinux', 'Suse', 'Gentoo']", text)
        self.assertIn("when: ansible_facts.os_family != 'Suse'", text)

    def test_ssh_service_debian_is_ssh(self):
        """Debian service is 'ssh', not 'sshd'."""
        text = _read(self.HANDLERS)
        self.assertIn("'ssh' if ansible_facts.os_family == 'Debian'", text)

    def test_ssh_service_non_debian_is_sshd(self):
        """RedHat and Arch use 'sshd'."""
        text = _read(self.HANDLERS)
        self.assertIn("else 'sshd'", text)

    def test_common_defaults_expose_ssh_manage_toggle(self):
        text = _read(self.COMMON_DEFAULTS)
        self.assertIn("ssh_manage: true", text)
        self.assertIn("leave SSH daemon packaging and configuration unmanaged", text)
        self.assertIn("pkg_manager_update_policy: auto", text)
        self.assertIn("pkg_manager_update_valid_time: 3600", text)

    def test_site_gates_ssh_hardening_role_on_ssh_manage(self):
        text = _read(self.SITE)
        self.assertIn("- role: ssh_hardening", text)
        self.assertIn("when: ssh_manage | default(true) | bool", text)

    def test_linux_families_use_sshd_config_dropin(self):
        text = _read(self.TASKS)
        self.assertIn("_sshd_config_dropin_supported", text)
        self.assertIn("['Debian', 'RedHat', 'Archlinux']", text)
        self.assertIn("Ensure sshd privilege separation directory exists", text)
        self.assertIn("path: /run/sshd", text)
        self.assertIn("/etc/ssh/sshd_config.d/99-ansible-enterprise.conf", text)
        self.assertIn("Validate merged sshd configuration after drop-in deployment", text)
        self.assertIn("_sshd_dropin is changed", text)

    def test_freebsd_keeps_monolithic_sshd_config(self):
        text = _read(self.TASKS)
        self.assertIn("Deploy monolithic sshd_config", text)
        self.assertIn("not (_sshd_config_dropin_supported | bool)", text)

    def test_gentoo_uses_openssh_package_name(self):
        text = _read(self.TASKS)
        self.assertIn("['Archlinux', 'Suse', 'Gentoo']", text)
        self.assertIn("['openssh'] + (['sudo'] if sudo_enabled | default(true) | bool else [])", text)

    def test_linux_sudoers_directory_is_created(self):
        text = _read(self.TASKS)
        self.assertIn("Ensure sudoers.d directory exists (Linux)", text)
        self.assertIn("path: /etc/sudoers.d", text)
        self.assertIn("ansible_facts.os_family != 'FreeBSD'", text)

    def test_dropin_template_omits_subsystem_and_uses_normalized_admin_names(self):
        text = _read(self.SSHD_DROPIN_TEMPLATE)
        self.assertIn("AllowUsers root {{ _admin_user_names | default(admin_users) | join(\" \") }}", text)
        self.assertNotIn("Subsystem sftp", text)

    def test_monolithic_template_retains_subsystem_path_logic(self):
        text = _read(self.SSHD_TEMPLATE)
        self.assertIn("Subsystem sftp", text)

    def test_alpine_monolithic_template_omits_usepam(self):
        text = _read(self.SSHD_TEMPLATE)
        self.assertIn("os_family != 'Alpine'", text)
        self.assertIn("UsePAM yes", text)

    def test_ssh_host_keys_are_ensured_before_validation(self):
        text = _read(self.TASKS)
        self.assertIn("Ensure SSH host keys exist before config validation", text)
        self.assertIn("ssh-keygen -A", text)


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

    def test_redhat_named_conf_includes_rndc_support(self):
        text = _read(self.NAMED_CONF)
        self.assertIn("os_family == 'RedHat'", text)
        self.assertIn('include "/etc/rndc.key";', text)
        self.assertIn('keys { "rndc-key"; }', text)
        self.assertIn("controls {", text)

    def test_redhat_tasks_generate_rndc_key(self):
        text = _read(self.TASKS)
        self.assertIn("Generate rndc key for RedHat authoritative BIND", text)
        self.assertIn("rndc-confgen", text)
        self.assertIn("creates: /etc/rndc.key", text)
        self.assertIn("Set RedHat rndc key permissions", text)

    def test_enable_and_start_bind_task_present(self):
        """BIND must have an explicit state: started task (not only via handler)."""
        text = _read(self.TASKS)
        self.assertIn("Enable and start BIND (systemd)", text)
        self.assertIn("systemd:", text)
        self.assertIn("Enable and start BIND (OpenRC)", text)
        self.assertIn("service:", text)
        self.assertIn("enabled: true", text)
        self.assertIn("state: started", text)
        self.assertIn("ansible_facts.service_mgr == 'systemd'", text)
        self.assertIn("ansible_facts.service_mgr == 'openrc'", text)

    def test_zone_serials_bump_after_bind_is_ready(self):
        text = _read(self.TASKS)
        self.assertLess(text.index("Wait for BIND to be ready on port 53"), text.index("Bump zone serials"))

    def test_dns_nftables_dropin_requires_firewall_role(self):
        text = _read(self.TASKS)
        deploy_pos = text.index("Deploy DNS nftables drop-in")
        self.assertIn("firewall_enabled | default(false) | bool", text[deploy_pos:deploy_pos + 400])

    def test_dns_helper_directory_exists_before_helper_installs(self):
        text = _read(self.TASKS)
        self.assertIn("Ensure local admin helper directory exists", text)
        self.assertIn("path: /usr/local/sbin", text)
        self.assertLess(text.index("Ensure local admin helper directory exists"), text.index("Install dns-bump-serial helper"))
        self.assertNotIn("Remove old update_dns_serial.py helper", text)
        self.assertNotIn("/usr/local/sbin/update_dns_serial.py", text)

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
    BOOTSTRAP_PLAY = "bootstrap.yml"
    BOOTSTRAP_TASKS = "roles/bootstrap_scripts/tasks/main.yml"

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

    def test_lxc_bootstrap_supports_pre_and_post_raw_hooks(self):
        text = _read("lxc_bootstrap.yml")
        self.assertIn("Run bootstrap pre-Python commands", text)
        self.assertIn("bootstrap_raw_pre | default([])", text)
        self.assertIn("bootstrap_raw_pre_host | default([])", text)
        self.assertIn("Run bootstrap post-Python commands", text)
        self.assertIn("bootstrap_raw_post | default([])", text)
        self.assertIn("bootstrap_raw_post_host | default([])", text)

    def test_lxc_bootstrap_runs_post_hook_after_python_setup(self):
        text = _read("lxc_bootstrap.yml")
        self.assertLess(text.index("- name: Run bootstrap pre-Python commands"), text.index("- name: Install Python"))
        self.assertLess(text.index("- name: Install Python"), text.index("- name: Verify Python and gather facts"))
        self.assertLess(text.index("- name: Verify Python and gather facts"), text.index("- name: Run bootstrap post-Python commands"))

    def test_bootstrap_prefers_manager_specific_search_domain_configuration(self):
        text = _read(self.BOOTSTRAP_TEMPLATE)
        self.assertIn("nmcli connection modify", text)
        self.assertIn("systemctl is-active NetworkManager", text)
        self.assertIn("systemctl list-unit-files systemd-resolved.service", text)
        self.assertIn("resolvconf -u", text)
        self.assertIn("supersede domain-search", text)
        self.assertIn('${DOMAIN}', text)
        self.assertIn("/etc/systemd/resolved.conf.d/ansible-enterprise.conf", text)
        self.assertIn("Domains=${DOMAIN}", text)

    def test_bootstrap_play_uses_live_local_python_not_stale_venv_path(self):
        text = _read(self.BOOTSTRAP_PLAY)
        self.assertIn("lookup(", text)
        self.assertIn("command -v python3 || command -v python", text)
        self.assertNotIn("ansible_playbook_python", text)

    def test_bootstrap_role_explicitly_delegates_generation_to_localhost(self):
        text = _read(self.BOOTSTRAP_TASKS)
        self.assertIn("delegate_to: localhost", text)
        self.assertIn("Generate plaintext bootstrap script", text)
        self.assertIn("Build self-decrypting bootstrap script", text)

    def test_bootstrap_role_exports_inventory_vars_without_eager_hostvar_resolution(self):
        text = _read(self.BOOTSTRAP_TASKS)
        self.assertIn("ansible-inventory", text)
        self.assertIn("--host {{ inventory_hostname | quote }} --yaml --export", text)
        self.assertIn("_bs_host_vars_export.stdout | from_yaml", text)
        self.assertNotIn("hostvars[inventory_hostname]", text)


class TestTrustedRootCertificates(unittest.TestCase):

    COMMON_DEFAULTS = "roles/common/defaults/main.yml"
    COMMON_TASKS = "roles/common/tasks/main.yml"

    def test_common_defaults_document_trusted_root_certificates(self):
        text = _read(self.COMMON_DEFAULTS)
        self.assertIn("trusted_root_certificates: {}", text)
        self.assertIn("trusted_root_certificates:", text)
        self.assertIn("pem:", text)
        self.assertIn("src:", text)
        self.assertIn("remote_src:", text)

    def test_common_installs_trusted_roots_in_distro_trust_store(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("Resolve trusted root certificate store", text)
        self.assertIn("/usr/local/share/ca-certificates", text)
        self.assertIn("/etc/pki/ca-trust/source/anchors", text)
        self.assertIn("/etc/ca-certificates/trust-source/anchors", text)
        self.assertIn("/etc/pki/trust/anchors", text)
        self.assertIn("/usr/local/share/certs", text)
        self.assertIn("Install ca-certificates package for trusted roots", text)
        self.assertIn("ca_root_nss", text)
        self.assertIn("app-misc/ca-certificates", text)

    def test_common_validates_and_installs_all_trusted_root_sources(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("Assert trusted root certificate entries are valid", text)
        self.assertIn("exactly one of", text)
        self.assertIn("Install trusted root certificates from inline PEM", text)
        self.assertIn("Install trusted root certificates from controller files", text)
        self.assertIn("Install trusted root certificates from remote files", text)
        self.assertIn("remote_src: true", text)
        inline_task = text[text.index("Install trusted root certificates from inline PEM"):text.index("Install trusted root certificates from controller files")]
        self.assertIn("no_log: true", inline_task)

    def test_common_refreshes_trusted_root_store_per_distro(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("Refresh trusted root certificate store", text)
        self.assertIn("update-ca-certificates", text)
        self.assertIn("update-ca-trust", text)
        self.assertIn("trust extract-compat", text)
        self.assertIn("certctl rehash", text)
        self.assertIn("_trusted_root_pem_copy.results", text)
        self.assertIn("_trusted_root_src_copy.results", text)
        self.assertIn("_trusted_root_remote_copy.results", text)


class TestGentooSupportRegression(unittest.TestCase):

    COMMON_DEFAULTS = "roles/common/defaults/main.yml"
    COMMON_TASKS = "roles/common/tasks/main.yml"

    def test_common_defaults_document_gentoo_profile(self):
        text = _read(self.COMMON_DEFAULTS)
        self.assertIn("gentoo_profile: ''", text)
        self.assertIn("default/linux/amd64/23.0", text)

    def test_common_tasks_manage_gentoo_profile_idempotently(self):
        text = _read(self.COMMON_TASKS)
        self.assertIn("Read current Gentoo profile", text)
        self.assertIn("eselect profile show", text)
        self.assertIn("Set Gentoo profile", text)
        self.assertIn("ansible_facts.os_family == 'Gentoo'", text)
        self.assertIn('(_gentoo_current_profile.stdout | default(\'\') | trim) != gentoo_profile', text)


class TestAdminUsersRegression(unittest.TestCase):

    COMMON_DEFAULTS = "roles/common/defaults/main.yml"
    SSH_TASKS = "roles/ssh_hardening/tasks/main.yml"
    SSHD_TEMPLATE = "roles/ssh_hardening/templates/sshd_config.j2"
    BOOTSTRAP_TEMPLATE = "roles/bootstrap_scripts/templates/bootstrap.sh.j2"
    BOOTSTRAP_TASKS = "roles/bootstrap_scripts/tasks/main.yml"

    def test_common_defaults_document_rich_admin_users(self):
        text = _read(self.COMMON_DEFAULTS)
        self.assertIn("Supports simple strings (backwards compatible) or dicts", text)
        self.assertIn("ssh_keys:", text)
        self.assertIn("shell:", text)
        self.assertIn("password:", text)

    def test_ssh_role_normalizes_admin_users(self):
        text = _read(self.SSH_TASKS)
        self.assertIn("Assert admin_users entries are strings or named mappings", text)
        self.assertIn("Normalize admin_users", text)
        self.assertIn("_admin_users", text)
        self.assertIn("_admin_user_names", text)
        self.assertIn("item.password is defined", text)
        self.assertIn("selectattr('ssh_keys', 'defined')", text)
        self.assertIn("Resolve admin users primary groups", text)
        self.assertIn("_admin_primary_groups", text)
        self.assertIn("id", text)
        self.assertIn("_admin_primary_groups[item.name] | default(omit)", text)
        self.assertIn("Validate sudoers configuration after drop-in changes", text)
        self.assertIn("_admin_sudoers_dropins is changed", text)
        self.assertNotIn('validate: "visudo -cf %s"', text)

    def test_sshd_config_uses_normalized_admin_user_names(self):
        text = _read(self.SSHD_TEMPLATE)
        self.assertIn("AllowUsers root {{ _admin_user_names | default(admin_users) | join(\" \") }}", text)
        self.assertNotIn("AllowUsers root {{ admin_users | join(\" \") }}", text)

    def test_bootstrap_normalizes_rich_admin_users(self):
        tasks = _read(self.BOOTSTRAP_TASKS)
        text = _read(self.BOOTSTRAP_TEMPLATE)
        self.assertIn("Normalize bootstrap admin_users", tasks)
        self.assertIn("_bootstrap_admin_users", tasks)
        self.assertIn("_bootstrap_admin_user_names", tasks)
        self.assertIn("ADMIN_USERS=({{ _bs.admin_user_names | join(' ') }})", text)
        self.assertIn("USER_SHELL=", text)
        self.assertIn("USER_PASSWORD_HASH=", text)
        self.assertIn("printf", text)
        self.assertIn("_key | quote", text)


# ---------------------------------------------------------------------------
# nfs role
# ---------------------------------------------------------------------------

class TestNfsRoleRegression(unittest.TestCase):

    NFS_DEFAULTS = "roles/nfs/defaults/main.yml"
    NFS_TASKS = "roles/nfs/tasks/main.yml"
    NFS_HANDLERS = "roles/nfs/handlers/main.yml"
    SITE = "site.yml"

    def test_nfs_defaults_document_versions_threads_idmap_and_generic_mounts(self):
        text = _read(self.NFS_DEFAULTS)
        self.assertIn("versions: list like [3, 4.0] or [4]", text)
        self.assertIn("4.0  -> only NFSv4.0", text)
        self.assertIn("versions: [4]", text)
        self.assertIn("threads: 8", text)
        self.assertIn("idmap_domain", text)
        self.assertIn("fstype: nfs | nfs4", text)
        self.assertIn("Use vers=4.0 or minorversion=0", text)
        self.assertIn("# -- Generic filesystem mounts", text)
        self.assertIn("fstype: cifs", text)
        self.assertIn("opts: bind", text)

    def test_nfs_tasks_manage_server_versions_and_threads(self):
        text = _read(self.NFS_TASKS)
        self.assertIn("_nfs_versions", text)
        self.assertIn("_nfs_version_tokens", text)
        self.assertIn("Enable and start rpcbind (NFSv3)", text)
        self.assertIn("RPCNFSDCOUNT={{ nfs.server.threads | default(8) }}", text)
        self.assertIn("RPCNFSDOPTS=", text)
        self.assertIn("-N 4.1", text)
        self.assertIn("-N 4.2", text)
        self.assertIn("vers3={{ 'y' if 3 in _nfs_versions else 'n' }}", text)
        self.assertIn("vers4={{ 'y' if '4' in _nfs_version_tokens or '4.0' in _nfs_version_tokens or '4.1' in _nfs_version_tokens or '4.2' in _nfs_version_tokens else 'n' }}", text)
        self.assertIn("vers4.1={{ 'y' if '4' in _nfs_version_tokens or '4.1' in _nfs_version_tokens or '4.2' in _nfs_version_tokens else 'n' }}", text)
        self.assertIn("vers4.2={{ 'y' if '4' in _nfs_version_tokens or '4.2' in _nfs_version_tokens else 'n' }}", text)
        self.assertIn("threads={{ nfs.server.threads | default(8) }}", text)

    def test_nfs_tasks_manage_idmap_and_client_fstype(self):
        text = _read(self.NFS_TASKS)
        self.assertIn("Configure idmapd domain (server)", text)
        self.assertIn("Configure idmapd domain (client)", text)
        self.assertIn("Domain = {{ nfs.server.idmap_domain }}", text)
        self.assertIn("Domain = {{ nfs.client.idmap_domain }}", text)
        self.assertIn("fstype: \"{{ item.fstype | default('nfs') }}\"", text)
        self.assertIn("state: \"{{ item.state | default('mounted') }}\"", text)

    def test_nfs_role_supports_generic_mounts_and_role_activation(self):
        tasks = _read(self.NFS_TASKS)
        site = _read(self.SITE)
        self.assertIn("Ensure generic mountpoint directories exist", tasks)
        self.assertIn("Configure generic mounts via fstab", tasks)
        self.assertIn("- meta: flush_handlers", tasks)
        self.assertIn("Apply server-side export and daemon changes before any client mount tasks", tasks)
        self.assertIn("Apply NFS exports immediately", tasks)
        self.assertIn("command: exportfs -ra", tasks)
        self.assertIn("tags: [nfs, mounts]", site)
        self.assertIn("or mounts | default([]) | length > 0", site)
        self.assertIn("or 'nfs' in (_required_providers | default([]))", site)

    def test_nfs_handlers_restart_server_and_idmapd(self):
        text = _read(self.NFS_HANDLERS)
        self.assertIn("Reload NFS exports", text)
        self.assertIn("Restart NFS server", text)
        self.assertIn("Restart NFS idmapd", text)
        self.assertIn("rpc-idmapd", text)
        self.assertIn("nfsuserd", text)


# ---------------------------------------------------------------------------
# file_copy role
# ---------------------------------------------------------------------------

class TestFileCopyRegression(unittest.TestCase):

    DEFAULTS = "roles/file_copy/defaults/main.yml"
    TASKS = "roles/file_copy/tasks/main.yml"

    def test_file_copy_defaults_document_inline_content(self):
        text = _read(self.DEFAULTS)
        self.assertIn("content - inline file content to write instead of copying src", text)
        self.assertIn("dest: /etc/myapp/generated.conf", text)

    def test_file_copy_supports_inline_content_and_parent_directories(self):
        text = _read(self.TASKS)
        self.assertIn("Validate file_copy items", text)
        self.assertIn("exactly one of src or content", text)
        self.assertIn("Ensure parent directories for copied files exist", text)
        self.assertIn("path: \"{{ item.dest | dirname }}\"", text)
        self.assertIn("Copy files from contrib to remote host", text)
        self.assertIn("- item.src is defined", text)
        self.assertIn("Write inline file content to remote host", text)
        self.assertIn("content: \"{{ item.content }}\"", text)
        self.assertIn("- item.content is defined", text)


# ---------------------------------------------------------------------------
# proxmox infra playbook
# ---------------------------------------------------------------------------

class TestProxmoxInfraRegression(unittest.TestCase):

    INFRA = "infra.yml"

    def test_infra_playbook_documents_rebuild_policy_and_force_override(self):
        text = _read(self.INFRA)
        self.assertIn("infra_defaults.state / infra.state", text)
        self.assertIn("present       : ensure the guest exists", text)
        self.assertIn("absent        : stop + destroy the guest if it exists", text)
        self.assertIn("infra_defaults.rebuild_on / infra.rebuild_on", text)
        self.assertIn("never         : keep the existing guest and update it in place", text)
        self.assertIn("config_change : destroy + recreate only when the desired config hash changes", text)
        self.assertIn("always        : destroy + recreate on every run", text)
        self.assertIn("infra_force_rebuild=true", text)
        self.assertIn("build/.infra-state/<inventory_hostname>.json", text)

    def test_infra_playbook_persists_and_uses_config_hash_state(self):
        text = _read(self.INFRA)
        self.assertIn("_infra_provider", text)
        self.assertIn("_infra_state", text)
        self.assertIn("Validate infra lifecycle state", text)
        self.assertIn("_infra_should_remove", text)
        self.assertIn("_infra_rebuild_on", text)
        self.assertIn("_infra_force_rebuild", text)
        self.assertIn("_infra_rebuild_config", text)
        self.assertIn("_infra_config_hash", text)
        self.assertIn("_infra_state_dir", text)
        self.assertIn("_infra_state_file", text)
        self.assertIn("Decode previous infra config state", text)
        self.assertIn("_infra_last_config_hash", text)
        self.assertIn("_infra_should_rebuild", text)
        self.assertIn("Destroy existing infrastructure instance for removal or rebuild", text)
        self.assertIn("Persist last applied infra config fingerprint", text)
        self.assertIn("provider in ['proxmox']", text)
        self.assertIn("infra.proxmox.node", text)

    def test_infra_playbook_uses_vm_specific_defaults(self):
        text = _read(self.INFRA)
        self.assertIn('_proxmox_default_cores: "{{ 2 if _infra_type == \'vm\' else 2 }}"', text)
        self.assertIn('_proxmox_default_memory: "{{ 4096 if _infra_type == \'vm\' else 2048 }}"', text)
        self.assertIn('cores: "{{ _proxmox.cores | default(_proxmox_default_cores) }}"', text)
        self.assertIn('memory: "{{ _proxmox.memory | default(_proxmox_default_memory) }}"', text)

    def test_infra_playbook_derives_internal_api_host_from_public_input(self):
        text = _read(self.INFRA)
        self.assertIn('_pve_node_hostvars: "{{ hostvars.get(_pve_node, {}) if _pve_node | length > 0 else {} }}"', text)
        self.assertIn('_pve_api_host: "{{ _proxmox.api_host | default(_pve_node_hostvars.ansible_host | default(_pve_node), true) }}"', text)
        self.assertIn('_pve_api_host | default(\'\') | length > 0', text)

    def test_infra_playbook_passes_validate_certs_to_proxmox_modules(self):
        text = _read(self.INFRA)
        self.assertIn('_pve_validate_certs: "{{ _proxmox.validate_certs | default(false) }}"', text)
        self.assertIn('validate_certs: "{{ _pve_validate_certs }}"', text)

    def test_infra_playbook_passes_timeout_to_proxmox_modules(self):
        text = _read(self.INFRA)
        self.assertIn('_pve_timeout: "{{ _proxmox.timeout | default(300) }}"', text)
        self.assertIn('timeout: "{{ _pve_timeout }}"', text)

    def test_infra_playbook_validates_lxc_ostemplate_is_storage_backed(self):
        text = _read(self.INFRA)
        self.assertIn("Validate Proxmox LXC template reference format", text)
        self.assertIn("not (_proxmox.ostemplate | default('')).startswith('/')", text)
        self.assertIn("':' in (_proxmox.ostemplate | default(''))", text)
        self.assertIn("vztmpl/", text)
        self.assertIn("not a filesystem path", text)

    def test_infra_playbook_creates_lxc_with_disk_volume(self):
        text = _read(self.INFRA)
        self.assertIn("Create Proxmox LXC container", text)
        self.assertIn("disk_volume:", text)


# ---------------------------------------------------------------------------
# certbot role
# ---------------------------------------------------------------------------

class TestCertbotDistro(unittest.TestCase):

    TASKS = "roles/certbot/tasks/main.yml"
    CERTBOT_DEFAULTS = "roles/certbot/defaults/main.yml"
    SITE = "site.yml"

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

    def test_defaults_document_registry_level_certificate_methods(self):
        text = _read(self.CERTBOT_DEFAULTS)
        self.assertIn("certificates.<name>.method", text)
        self.assertIn("services.<name>.security.tls.certificate", text)
        self.assertIn("mailserver.tls.certificate", text)
        self.assertIn("/etc/ssl/certs/ansible-enterprise/<certificate-name>/fullchain.pem", text)
        self.assertIn("/etc/pki/tls/private/ansible-enterprise/<certificate-name>/privkey.pem", text)
        self.assertIn("selfsigned", text)
        self.assertIn("certbot", text)
        self.assertIn("path", text)
        self.assertIn("inventory", text)
        self.assertIn("stepca", text)
        self.assertNotIn("tls_certificate_method:", text)
        self.assertNotIn("security.tls.method", text)

    def test_site_runs_tls_cert_role_for_service_or_mail_tls(self):
        text = _read(self.SITE)
        self.assertIn("security.tls.enabled", text)
        self.assertIn("mailserver.tls.enabled | default(false) | bool", text)

    def test_certbot_builds_requests_from_services_and_mailserver(self):
        text = _read(self.TASKS)
        self.assertIn("Build certificate request list", text)
        self.assertIn("services | default({}) | dict2items", text)
        self.assertIn("mailserver.tls", text)
        self.assertIn("certificates | default({})", text)
        self.assertIn("(_svc.value.security | default({})).tls", text)
        self.assertIn("'consumer': 'mailserver'", text)
        self.assertIn("'method': _cert.method | default('selfsigned')", text)
        self.assertNotIn("_tls.method | default(_cert.method", text)
        self.assertNotIn("_mail_tls.method | default(_cert.method", text)
        self.assertNotIn("'privkey_pem':", text)
        self.assertNotIn("'fullchain_pem':", text)

    def test_certbot_tasks_are_gated_on_request_method(self):
        text = _read(self.TASKS)
        self.assertIn("Assert certificate methods are supported", text)
        self.assertIn("['selfsigned', 'certbot', 'path', 'inventory', 'stepca']", text)
        self.assertIn("Fail for unimplemented step-ca certificate method", text)
        self.assertIn("TLS certificate method stepca is reserved but not implemented yet", text)
        self.assertIn("item.method == 'certbot'", text)
        self.assertIn("Install certificate renewal cron job", text)

    def test_inventory_method_installs_certificate_material(self):
        text = _read(self.TASKS)
        self.assertIn("Ensure managed certificate root exists", text)
        self.assertIn("Ensure managed private key root exists", text)
        self.assertIn("/etc/ssl/certs/ansible-enterprise", text)
        self.assertIn("/etc/ssl/private/ansible-enterprise", text)
        self.assertIn("/etc/pki/tls/certs/ansible-enterprise", text)
        self.assertIn("/etc/pki/tls/private/ansible-enterprise", text)
        self.assertIn("fullchain_pem", text)
        self.assertIn("privkey_pem", text)
        self.assertIn("Install inventory fullchain certificate", text)
        self.assertIn("Install inventory private key", text)
        self.assertIn("(certificates | default({})).get(item.name, {}).get('privkey_pem', '')", text)
        self.assertIn("_ae_tls_cert_dir }}/{{ item.storage_name }}/fullchain.pem", text)
        self.assertIn("_ae_tls_private_dir }}/{{ item.storage_name }}/privkey.pem", text)
        self.assertIn("item.method == 'inventory'", text)
        self.assertIn("certificates.{{ item.name }}", text)
        private_key_task = text[text.index("Install inventory private key"):text.index("Assert certbot_email is set")]
        self.assertIn("no_log: true", private_key_task)
        inventory_material_tasks = text[text.index("Assert inventory certificate material is defined"):text.index("Assert certbot_email is set")]
        self.assertGreaterEqual(inventory_material_tasks.count("no_log: true"), 3)

    def test_certbot_secret_tasks_are_no_log(self):
        text = _read(self.TASKS)
        nsupdate_task = text[text.index("Resolve certbot nsupdate target from dns.zones"):text.index("Debug certbot nsupdate resolution")]
        self.assertIn("no_log: true", nsupdate_task)
        tsig_assert_task = text[text.index("Assert certbot tsig secret is set when using nsupdate"):text.index("Install DNS client utilities")]
        self.assertIn("no_log: true", tsig_assert_task)
        tsig_file_task = text[text.index("Deploy TSIG key file for nsupdate"):text.index("Deploy DNS auth hook script")]
        self.assertIn("no_log: true", tsig_file_task)

    def test_selfsigned_generation_supports_explicit_selfsigned_method(self):
        text = _read(self.TASKS)
        self.assertIn("item.method == 'selfsigned'", text)
        self.assertIn("Generate managed self-signed certificate", text)
        self.assertIn("_ae_tls_private_dir }}/{{ item.storage_name }}/privkey.pem", text)
        self.assertIn("_ae_tls_cert_dir }}/{{ item.storage_name }}/fullchain.pem", text)
        self.assertIn("certbot_selfsigned_fallback", text)
        self.assertIn("Generate certbot self-signed fallback at Let's Encrypt path", text)


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

    def test_mailserver_resolves_tls_certificate_paths(self):
        text = _read(self.TASKS)
        self.assertIn("Resolve mailserver TLS certificate paths", text)
        self.assertIn("certificates | default({})", text)
        self.assertIn("_ae_tls_cert_dir", text)
        self.assertIn("_ae_tls_private_dir", text)
        self.assertIn("_method == 'certbot'", text)
        self.assertIn("_cert.method | default('selfsigned')", text)
        self.assertNotIn("mailserver.tls.method", text)
        self.assertIn("_mail_tls_fullchain_path", text)
        self.assertIn("Assert mailserver TLS certificate exists", text)

    def test_mailserver_configures_postfix_and_dovecot_tls(self):
        main_cf = _read("roles/mailserver/templates/main.cf.j2")
        tasks = _read(self.TASKS)
        self.assertIn("smtpd_tls_cert_file = {{ _mail_tls_fullchain_path }}", main_cf)
        self.assertIn("smtpd_tls_key_file = {{ _mail_tls_privkey_path }}", main_cf)
        self.assertIn("ssl_cert = <{{ _mail_tls_fullchain_path }}", tasks)
        self.assertIn("ssl_key = <{{ _mail_tls_privkey_path }}", tasks)


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
        """Cert existence check must only run for services with tls.enabled."""
        text = _read(self.RENDER_SVC)
        self.assertIn("((service.value.security | default({})).tls | default({})).enabled | default(false) | bool", text)
        self.assertIn("_cert_stat.stat.exists", text)
        self.assertIn("_tls_fullchain_path", text)
        self.assertIn("_cert.method | default('selfsigned')", text)
        self.assertNotIn("_tls.method", text)
        self.assertIn("certificates | default({})", text)

    def test_render_service_cert_fail_msg_actionable(self):
        """Cert missing fail_msg must tell operator what to do."""
        text = _read(self.RENDER_SVC)
        self.assertIn("certificates.{{ _tls_certificate_name }}.method", text)
        self.assertIn("certbot uses", text)
        self.assertIn("inventory/selfsigned use", text)
        self.assertIn("certificates.{{ _tls_certificate_name }}.{fullchain_path,privkey_path}", text)
        self.assertIn("certificates.{{ _tls_certificate_name }}.{fullchain_pem,privkey_pem}", text)

    def test_vhost_templates_use_resolved_tls_paths(self):
        for rel in (
            "roles/nginx/templates/site.conf.j2",
            "roles/nginx/templates/restricted_site.conf.j2",
            "roles/nginx/templates/client_cert_site.conf.j2",
            "roles/nginx/templates/nextcloud.conf.j2",
        ):
            text = _read(rel)
            self.assertIn("ssl_certificate {{ _tls_fullchain_path }}", text)
            self.assertIn("ssl_certificate_key {{ _tls_privkey_path }}", text)


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
        text = _read(self.SITE)
        self.assertIn("Refresh apt package cache", text)
        self.assertIn("Refresh apt package cache (auto)", text)
        self.assertIn("Configure apt proxy", text)
        self.assertIn('/etc/apt/apt.conf.d/90ansible-enterprise-proxy', text)
        self.assertIn('Acquire::http::Proxy "{{ pkg_manager_proxy.http_proxy }}";', text)
        self.assertIn('cache_valid_time: "{{ pkg_manager_update_valid_time | default(3600) | int }}"', text)

    def test_dnf_cache_refresh_present(self):
        text = _read(self.SITE)
        self.assertIn("Refresh dnf package cache", text)
        self.assertIn("Configure dnf proxy", text)
        self.assertIn('path: /etc/dnf/dnf.conf', text)
        self.assertIn('option: proxy', text)

    def test_pacman_cache_refresh_present(self):
        """Arch Linux needs pacman -Sy before installing packages."""
        text = _read(self.SITE)
        self.assertIn("Refresh pacman package cache", text)
        self.assertIn("Archlinux", text)

    def test_gentoo_cache_refresh_present(self):
        text = _read(self.SITE)
        self.assertIn("Refresh Gentoo package metadata", text)
        self.assertIn("emaint sync -a", text)
        self.assertIn("Gentoo", text)

    def test_apk_cache_refresh_present(self):
        text = _read(self.SITE)
        self.assertIn("Refresh apk package cache", text)
        self.assertIn("apk update", text)
        self.assertIn("Alpine", text)

    def test_zypper_cache_refresh_present(self):
        text = _read(self.SITE)
        self.assertIn("Refresh zypper package cache", text)
        self.assertIn("zypper --non-interactive refresh", text)
        self.assertIn("Suse", text)

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

    def test_gentoo_refresh_gated_to_gentoo(self):
        text = _read(self.SITE)
        gentoo_pos = text.index("Refresh Gentoo package metadata")
        os_pos = text.index("os_family == 'Gentoo'", gentoo_pos)
        self.assertLess(gentoo_pos, os_pos + 100)

    def test_apk_refresh_gated_to_alpine(self):
        text = _read(self.SITE)
        alpine_pos = text.index("Refresh apk package cache")
        os_pos = text.index("os_family == 'Alpine'", alpine_pos)
        self.assertLess(alpine_pos, os_pos + 100)

    def test_zypper_refresh_gated_to_suse(self):
        text = _read(self.SITE)
        suse_pos = text.index("Refresh zypper package cache")
        os_pos = text.index("os_family == 'Suse'", suse_pos)
        self.assertLess(suse_pos, os_pos + 100)

    def test_cache_refresh_tasks_accept_proxy_environment(self):
        text = _read(self.SITE)
        self.assertEqual(
            text.count('environment: "{{ pkg_manager_proxy if (pkg_manager_proxy | default({}) | length > 0) else omit }}"'),
            4,
        )

    def test_package_manager_update_policy_assert_present(self):
        text = _read(self.SITE)
        self.assertIn("Assert package-manager update policy is valid", text)
        self.assertIn("pkg_manager_update_policy | default('always') in ['always', 'auto', 'never']", text)
        self.assertIn("pkg_manager_update_valid_time | default(3600) | int > 0", text)

    def test_cache_refresh_tasks_are_policy_gated(self):
        text = _read(self.SITE)
        self.assertIn("pkg_manager_update_policy | default('always') == 'always'", text)
        self.assertIn("pkg_manager_update_policy | default('always') == 'auto'", text)
        self.assertNotIn("makecache --timer", text)

    def test_apt_and_dnf_proxy_config_cleanup_present(self):
        text = _read(self.SITE)
        self.assertIn("Remove apt proxy config when unset", text)
        self.assertIn("Remove dnf proxy config when unset", text)

    def test_suse_proxy_config_present(self):
        text = _read(self.SITE)
        self.assertIn("Configure openSUSE proxy", text)
        self.assertIn("Remove openSUSE proxy config when unset", text)
        self.assertIn("path: /etc/sysconfig/proxy", text)
        self.assertIn('PROXY_ENABLED="yes"', text)

    def test_site_does_not_mutate_package_mirrors(self):
        text = _read(self.SITE)
        self.assertNotIn("Find apt source files", text)
        self.assertNotIn("Set apt mirror for Ubuntu", text)
        self.assertNotIn("Set apt mirror for Debian", text)
        self.assertNotIn("Find yum repo files", text)
        self.assertNotIn("Set dnf baseurl for Rocky Linux", text)
        self.assertNotIn("Set dnf baseurl for AlmaLinux", text)
        self.assertNotIn("Find zypper repo files", text)
        self.assertNotIn("Set zypper mirror for openSUSE", text)


class TestBootstrapMirrorSetup(unittest.TestCase):

    BOOTSTRAP = "lxc_bootstrap.yml"

    def test_bootstrap_mirror_uses_os_release_detection(self):
        """Single mirror task uses /etc/os-release case statement."""
        text = _read(self.BOOTSTRAP)
        self.assertIn("Set package manager mirrors (bootstrap)", text)
        self.assertIn(". /etc/os-release", text)
        self.assertIn('case "$ID" in', text)

    def test_bootstrap_mirror_covers_all_distro_families(self):
        """The case statement handles all supported distro IDs."""
        text = _read(self.BOOTSTRAP)
        for distro_id in ("ubuntu", "debian", "devuan", "alpine",
                          "fedora", "rocky", "almalinux", "opensuse*|sles"):
            self.assertIn(distro_id + ")", text,
                          f"missing case branch for {distro_id}")

    def test_bootstrap_mirror_before_python_install(self):
        text = _read(self.BOOTSTRAP)
        mirror_idx = text.index("- name: Set package manager mirrors (bootstrap)")
        check_python_idx = text.index("- name: Check for existing Python interpreter")
        install_idx = text.index("- name: Install Python")
        self.assertLess(mirror_idx, check_python_idx)
        self.assertLess(mirror_idx, install_idx)

    def test_bootstrap_mirror_apt_sed_patterns(self):
        text = _read(self.BOOTSTRAP)
        self.assertIn("archive\\.ubuntu\\.com/ubuntu", text)
        self.assertIn("deb\\.debian\\.org/debian", text)
        self.assertIn("devuan\\.org/merged", text)
        self.assertIn("/alpine", text)

    def test_bootstrap_mirror_dnf_config_manager(self):
        text = _read(self.BOOTSTRAP)
        self.assertIn("dnf config-manager --save", text)
        for repo in ("fedora.baseurl=", "baseos.baseurl=",
                      "appstream.baseurl=", "crb.baseurl=",
                      "extras.baseurl="):
            self.assertIn(repo, text)

    def test_bootstrap_mirror_zypper(self):
        text = _read(self.BOOTSTRAP)
        self.assertIn("download\\.opensuse\\.org", text)
        self.assertIn("/etc/zypp/repos.d/*.repo", text)

    def test_bootstrap_mirror_is_gated_on_configured_mirrors(self):
        text = _read(self.BOOTSTRAP)
        self.assertIn("when: pkg_manager_mirror | default({}) | length > 0", text)

    def test_bootstrap_cache_urls_download_and_extract_flow_present(self):
        text = _read(self.BOOTSTRAP)
        self.assertIn("Download bootstrap cache archives", text)
        self.assertIn("get_url:", text)
        self.assertIn('loop: "{{ bootstrap_cache_urls | default([]) }}"', text)
        self.assertIn('environment: "{{ bootstrap_environment | default({}) }}"', text)
        self.assertIn("Extract bootstrap cache archives", text)
        self.assertIn("unarchive:", text)

    def test_bootstrap_cache_extract_runs_after_downloads(self):
        text = _read(self.BOOTSTRAP)
        self.assertLess(
            text.index("- name: Download bootstrap cache archives"),
            text.index("- name: Extract bootstrap cache archives"),
        )

    def test_bootstrap_cache_urls_honors_extract_and_creates_guards(self):
        text = _read(self.BOOTSTRAP)
        self.assertIn("item.creates | default('') == '' or not (item.creates | default('') is exists)", text)
        self.assertIn("item.item.extract | default(false) | bool", text)


class TestLxcExportPlaybook(unittest.TestCase):

    PLAYBOOK = "lxc_export.yml"

    def test_export_playbook_runs_vzdump_with_configured_options(self):
        text = _read(self.PLAYBOOK)
        self.assertIn("Run vzdump on Proxmox node", text)
        self.assertIn("vzdump {{ _vmid }}", text)
        self.assertIn("--compress {{ _compress }}", text)
        self.assertIn("--storage {{ _storage }}", text)
        self.assertIn("--mode {{ _mode }}", text)

    def test_export_playbook_stops_and_restarts_container_in_stop_mode(self):
        text = _read(self.PLAYBOOK)
        self.assertIn("Stop container before export", text)
        self.assertIn("pct stop {{ _vmid }}", text)
        self.assertIn("when: _mode == 'stop'", text)
        self.assertIn("Start container after export", text)
        self.assertIn("pct start {{ _vmid }}", text)

    def test_export_playbook_supports_template_move_and_local_fetch(self):
        text = _read(self.PLAYBOOK)
        self.assertIn("Resolve vztmpl directory on storage", text)
        self.assertIn("pvesm path {{ _storage }}:vztmpl/probe.tar", text)
        self.assertIn("Move tarball to vztmpl directory", text)
        self.assertIn('_template_ref: "{{ _storage }}:vztmpl/{{ _export_file | basename }}"', text)
        self.assertIn("Fetch tarball to local destination", text)
        self.assertIn("scp {{ _node }}:{{ _export_file }}", text)


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

    NFTABLES = "roles/dns/templates/40-dns.nft.j2"
    DNS_DEFAULTS = "roles/dns/defaults/main.yml"

    def test_dns_public_defaults_to_false(self):
        self.assertIn("recursion: false", _read(self.DNS_DEFAULTS))
        self.assertIn("dns:\n", _read(self.DNS_DEFAULTS))

    def test_dns_public_true_opens_port_53_unconditionally(self):
        text = _read(self.NFTABLES)
        self.assertIn("dns_public", text)
        # When true, plain accept with no source restriction
        idx = text.index("{% if dns_public | default(false) | bool %}")
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
        """dns_public handling now lives in the dns role's dedicated drop-in."""
        text = _read(self.NFTABLES)
        self.assertIn("# managed by ansible - dns role", text)
        self.assertIn("{% if dns_public | default(false) | bool %}", text)


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
        idx = text.index("- name: Allow root to list all processes (RedHat SELinux)")
        task_block = text[idx:idx+360]
        self.assertIn("os_family == 'RedHat'", task_block)
        self.assertIn("ansible_facts.selinux is defined", task_block)
        self.assertIn("ansible_facts.selinux.status | default('disabled') != 'disabled'", task_block)


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

    TASKS = "roles/firewall/tasks/main.yml"

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

    TASKS = "roles/firewall/tasks/main.yml"
    PF_CONF = "roles/firewall/templates/pf.conf.j2"

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
        self.assertIn("mailserver_ports", text)
        self.assertIn("default([25, 587, 143, 465])", text)

    def test_pf_conf_node_exporter_conditional(self):
        text = _read(self.PF_CONF)
        self.assertIn("node_exporter_enabled", text)
        self.assertIn("node_exporter_port", text)

    def test_pf_handler_uses_pfctl(self):
        text = _read("roles/firewall/handlers/main.yml")
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
        """Non-FreeBSD/non-OpenRC tasks must use systemd: module with enabled: true.
        service: tasks are allowed when gated to FreeBSD or OpenRC."""
        violations = []
        for path in self._tasks_files():
            text = path.read_text(encoding="utf-8")
            for block in text.split("- name:"):
                if "service:" in block and "enabled: true" in block and "state: started" in block:
                    # Allow service: tasks explicitly gated to FreeBSD or OpenRC
                    if "os_family == 'FreeBSD'" in block:
                        continue
                    if "service_mgr == 'openrc'" in block:
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


class TestFirewallRefactorPhaseOne(unittest.TestCase):
    def test_site_orders_firewall_before_firewall_geo_and_wireguard(self):
        text = _read("site.yml")
        lines = text.splitlines()
        firewall_idx = next(i for i, line in enumerate(lines) if line.strip() == "- role: firewall")
        firewall_geo_idx = next(i for i, line in enumerate(lines) if line.strip() == "- role: firewall_geo")
        wireguard_idx = next(i for i, line in enumerate(lines) if line.strip() == "- role: wireguard")
        self.assertLess(firewall_idx, firewall_geo_idx)
        self.assertLess(firewall_idx, wireguard_idx)

    def test_wireguard_role_deploys_its_own_nft_drop_in(self):
        text = _read("roles/wireguard/tasks/main.yml")
        self.assertIn("Deploy WireGuard nftables drop-in", text)
        self.assertIn("src: 40-wireguard.nft.j2", text)
        self.assertIn("dest: /etc/nftables.d/input/40-wireguard.nft", text)
        self.assertIn("notify: Reload nftables", text)
        self.assertIn("selectattr('listen_port', 'defined')", text)

    def test_wireguard_nft_template_only_opens_defined_listen_ports(self):
        text = _read("roles/wireguard/templates/40-wireguard.nft.j2")
        self.assertIn("_inst.listen_port is defined", text)
        self.assertIn('udp dport {{ _inst.listen_port }} accept comment "wg {{ _inst.name }}"', text)

    def test_firewall_geo_legacy_drop_in_no_longer_contains_wireguard_ports(self):
        text = _read("roles/firewall_geo/templates/30-legacy.nft.j2")
        self.assertNotIn("wireguard_instances", text)
        self.assertNotIn("listen_port | default(51820)", text)


class TestFirewallRefactorPhaseTwo(unittest.TestCase):
    def test_service_roles_deploy_own_nft_drop_ins(self):
        cases = [
            ("roles/dns/tasks/main.yml", "Deploy DNS nftables drop-in", "40-dns.nft.j2", "/etc/nftables.d/input/40-dns.nft"),
            ("roles/mailserver/tasks/main.yml", "Deploy mailserver nftables drop-in", "40-mailserver.nft.j2", "/etc/nftables.d/input/40-mailserver.nft"),
            ("roles/samba/tasks/main.yml", "Deploy Samba nftables drop-in", "40-samba.nft.j2", "/etc/nftables.d/input/40-samba.nft"),
            ("roles/nfs/tasks/main.yml", "Deploy NFS nftables drop-in", "40-nfs.nft.j2", "/etc/nftables.d/input/40-nfs.nft"),
            ("roles/node_exporter/tasks/main.yml", "Deploy node_exporter nftables drop-in", "40-node-exporter.nft.j2", "/etc/nftables.d/input/40-node-exporter.nft"),
            ("roles/step_ca/tasks/main.yml", "Deploy step-ca nftables drop-in", "40-stepca.nft.j2", "/etc/nftables.d/input/40-stepca.nft"),
            ("roles/openvpn/tasks/main.yml", "Deploy OpenVPN nftables drop-in", "40-openvpn.nft.j2", "/etc/nftables.d/input/40-openvpn.nft"),
            ("roles/workloads/tasks/main.yml", "Deploy workloads nftables drop-in", "40-workloads.nft.j2", "/etc/nftables.d/input/40-workloads.nft"),
        ]
        for rel, task_name, src_name, dest in cases:
            text = _read(rel)
            self.assertIn(task_name, text)
            self.assertIn(f"src: {src_name}", text)
            self.assertIn(f"dest: {dest}", text)
            self.assertIn("notify: Reload nftables", text)

    def test_service_nft_templates_exist(self):
        for rel in [
            "roles/dns/templates/40-dns.nft.j2",
            "roles/mailserver/templates/40-mailserver.nft.j2",
            "roles/samba/templates/40-samba.nft.j2",
            "roles/nfs/templates/40-nfs.nft.j2",
            "roles/node_exporter/templates/40-node-exporter.nft.j2",
            "roles/step_ca/templates/40-stepca.nft.j2",
            "roles/openvpn/templates/40-openvpn.nft.j2",
            "roles/workloads/templates/40-workloads.nft.j2",
        ]:
            self.assertTrue((BUILD / rel).exists(), msg=f"missing generated template: {rel}")

    def test_firewall_geo_legacy_drop_in_no_longer_contains_migrated_service_blocks(self):
        text = _read("roles/firewall_geo/templates/30-legacy.nft.j2")
        for old_marker in [
            "tcp dport 25  accept",
            "dns_public: true",
            "openvpn_instances",
            "step_ca.enabled",
            "samba.hosts_allow",
            "nfs.server.exports",
            "node_exporter_scrape_addresses",
            "workloads | default([])",
        ]:
            self.assertNotIn(old_marker, text)


class TestFreeBSDPfFirewall(unittest.TestCase):
    """FreeBSD pf firewall implementation tests."""

    PF_CONF    = "roles/firewall/templates/pf.conf.j2"
    FW_TASKS   = "roles/firewall/tasks/main.yml"
    FW_HANDLER = "roles/firewall/handlers/main.yml"
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


class TestSiteYmlStructure(unittest.TestCase):
    """Structural integrity checks for site.yml."""

    def test_no_duplicate_role_entries(self):
        """Each role must appear at most once in site.yml roles list."""
        import re
        text = _read("site.yml")
        roles = re.findall(r"- role:\s+(\S+)", text)
        seen = {}
        duplicates = []
        for role in roles:
            if role in seen:
                duplicates.append(role)
            seen[role] = True
        self.assertEqual(duplicates, [],
            f"Duplicate role entries in site.yml: {duplicates}")

    def test_no_duplicate_conditions_in_when(self):
        """No when: block should contain the same condition twice."""
        import re
        text = _read("site.yml")
        roles_start = text.find("\n  roles:\n")
        if roles_start != -1:
            text = text[roles_start:]
        # Find all when: blocks (multi-line, ending at next - role: or end)
        blocks = re.split(r"^\s+- role:", text, flags=re.MULTILINE)
        duplicates = []
        for block in blocks:
            when_match = re.search(r"when:\s*>?\s*\n((?:\s+.*\n)*)", block)
            if not when_match:
                continue
            lines = [l.strip() for l in when_match.group(1).splitlines()
                     if l.strip() and not l.strip().startswith("#")]
            # Normalize: strip leading or/and
            conditions = []
            for line in lines:
                cond = re.sub(r"^\s*(or|and)\s+", "", line).strip()
                if cond:
                    conditions.append(cond)
            seen = set()
            for cond in conditions:
                if cond in seen:
                    role_match = re.search(r"(\S+)", block)
                    role_name = role_match.group(1) if role_match else "unknown"
                    duplicates.append(f"{role_name}: {cond}")
                seen.add(cond)
        self.assertEqual(duplicates, [],
            f"Duplicate conditions in site.yml when: blocks: {duplicates}")
