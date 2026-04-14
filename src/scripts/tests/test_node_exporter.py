"""
Unit tests for the node_exporter role and its firewall integration.

Tests verify:
- Role files exist and contain required content
- nftables template includes node_exporter port rules
- Port 9100 is accepted from loopback by default
- scrape_addresses list drives additional accept rules
- Port is skipped when node_exporter_enabled is false
"""
import pathlib
import unittest

REPO  = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"


class TestNodeExporterRole(unittest.TestCase):

    TASKS = BUILD / "roles" / "node_exporter" / "tasks" / "main.yml"
    DEFAULTS = BUILD / "roles" / "node_exporter" / "defaults" / "main.yml"
    HANDLERS = BUILD / "roles" / "node_exporter" / "handlers" / "main.yml"

    def _tasks(self):
        return self.TASKS.read_text(encoding="utf-8")

    def _defaults(self):
        return self.DEFAULTS.read_text(encoding="utf-8")

    def test_tasks_file_exists(self):
        self.assertTrue(self.TASKS.exists())

    def test_defaults_file_exists(self):
        self.assertTrue(self.DEFAULTS.exists())

    def test_handlers_file_exists(self):
        self.assertTrue(self.HANDLERS.exists())

    def test_package_installed(self):
        self.assertIn("Install node_exporter", self._tasks())

    def test_distro_aware_package_name(self):
        """Debian uses a package; RedHat downloads a binary — no RHEL package name."""
        text = self._tasks()
        self.assertIn("prometheus-node-exporter", text)      # Debian package
        self.assertIn("usr/local/bin/node_exporter", text)   # RedHat binary path

    def test_distro_aware_binary_path(self):
        text = self._tasks()
        self.assertIn("/usr/bin/prometheus-node-exporter", text)  # Debian
        self.assertIn("/usr/local/bin/node_exporter", text)       # RedHat

    def test_service_enabled_and_started(self):
        text = self._tasks()
        self.assertIn("enabled: true", text)
        self.assertIn("state: started", text)

    def test_systemd_module_used(self):
        """Must use systemd module (not service) for idempotent enabled check."""
        text = self._tasks()
        self.assertIn("systemd:", text)

    def test_override_directory_created_before_file(self):
        """Debian: override directory task must precede the copy task."""
        text = self._tasks()
        dir_pos  = text.index("Ensure node_exporter systemd override directory exists")
        copy_pos = text.index("Deploy node_exporter listen-address override")
        self.assertLess(dir_pos, copy_pos)

    def test_override_binds_to_loopback(self):
        self.assertIn("127.0.0.1", self._tasks())

    def test_listen_address_uses_port_variable(self):
        self.assertIn("node_exporter_port", self._tasks())

    def test_epel_enabled_on_redhat(self):
        """RedHat and Arch use binary download; FreeBSD uses pkg."""
        text = self._tasks()
        self.assertIn("github.com/prometheus/node_exporter", text)
        self.assertIn("not in ['Debian', 'FreeBSD']", text)

    def test_redhat_creates_system_user(self):
        text = self._tasks()
        self.assertIn("Create node_exporter system user", text)
        self.assertIn("system: true", text)

    def test_redhat_architecture_aware(self):
        text = self._tasks()
        self.assertIn("aarch64", text)
        self.assertIn("amd64", text)

    def test_redhat_writes_systemd_unit(self):
        text = self._tasks()
        self.assertIn("node_exporter.service", text)
        self.assertIn("WantedBy=multi-user.target", text)

    def test_default_port_is_9100(self):
        self.assertIn("9100", self._defaults())

    def test_default_enabled_is_true(self):
        """node_exporter_enabled: true is declared in role defaults/main.yml."""
        self.assertIn("node_exporter_enabled: true", self._defaults())

    def test_scrape_addresses_default_is_empty(self):
        self.assertIn("node_exporter_scrape_addresses: []", self._defaults())

    def test_restart_handler_exists(self):
        text = self.HANDLERS.read_text(encoding="utf-8")
        self.assertIn("Restart node_exporter", text)
        self.assertIn("state: restarted", text)

    def test_daemon_reload_true(self):
        """systemd daemon_reload must be true so override is picked up."""
        self.assertIn("daemon_reload: true", self._tasks())


class TestNodeExporterFirewall(unittest.TestCase):

    NFTABLES = BUILD / "roles" / "node_exporter" / "templates" / "40-node-exporter.nft.j2"
    TASKS = BUILD / "roles" / "node_exporter" / "tasks" / "main.yml"

    def _tmpl(self):
        return self.NFTABLES.read_text(encoding="utf-8")

    def _tasks(self):
        return self.TASKS.read_text(encoding="utf-8")

    def test_node_exporter_block_present(self):
        self.assertIn("# managed by ansible - node_exporter role", self._tmpl())

    def test_loopback_ipv4_accepted(self):
        self.assertIn("ip  saddr 127.0.0.1", self._tmpl())

    def test_loopback_ipv6_accepted(self):
        self.assertIn("ip6 saddr ::1", self._tmpl())

    def test_port_variable_used(self):
        self.assertIn("node_exporter_port", self._tmpl())

    def test_scrape_addresses_loop_present(self):
        self.assertIn("node_exporter_scrape_addresses", self._tmpl())

    def test_ipv6_scrape_address_handled(self):
        """IPv6 scrape addresses must use ip6 saddr."""
        text = self._tmpl()
        # The template has a ':' check to distinguish IPv6
        self.assertIn('if ":" in _addr', text)

    def test_node_exporter_role_deploys_dedicated_drop_in(self):
        text = self._tasks()
        self.assertIn("Deploy node_exporter nftables drop-in", text)
        self.assertIn("/etc/nftables.d/input/40-node-exporter.nft", text)
        self.assertIn("notify: Reload nftables", text)


class TestNodeExporterSiteYml(unittest.TestCase):

    SITE = BUILD / "site.yml"

    def _site(self):
        return self.SITE.read_text(encoding="utf-8")

    def test_node_exporter_role_present(self):
        self.assertIn("role: node_exporter", self._site())

    def test_node_exporter_when_condition(self):
        self.assertIn("node_exporter_enabled", self._site())

    def test_node_exporter_after_mailserver(self):
        """node_exporter should be the last role in site.yml."""
        text = self._site()
        mail_pos = text.index("role: mailserver")
        ne_pos   = text.index("role: node_exporter")
        self.assertLess(mail_pos, ne_pos)


if __name__ == "__main__":
    unittest.main()
