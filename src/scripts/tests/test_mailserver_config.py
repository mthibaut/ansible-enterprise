"""
Unit tests for mailserver configuration: main.cf.j2 template and
roles/mailserver/defaults/main.yml.

Covers:
- mydestination includes mailserver.domain and localhost (not localhost only)
- mydestination includes local_domains list entries
- relay_domains rendered when relay_domains list is non-empty
- relay_domains absent when list is empty
- Both new keys present in defaults dict
- Flat variable documentation present in defaults
- Mailserver firewall templates derive from mailserver_ports
"""
import pathlib
import unittest

REPO  = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"


def _read(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


class TestMainCfTemplate(unittest.TestCase):

    TMPL = "roles/mailserver/templates/main.cf.j2"

    def test_mydestination_includes_mailserver_domain(self):
        """mydestination must include mailserver.domain, not just localhost."""
        text = _read(self.TMPL)
        # Find the actual directive line (not the comment)
        directive = [l for l in text.splitlines() if l.startswith("mydestination =")][0]
        self.assertIn("mailserver.domain", directive)

    def test_mydestination_includes_localhost(self):
        text = _read(self.TMPL)
        self.assertIn("localhost", text.split("mydestination")[1][:100])

    def test_mydestination_iterates_local_domains(self):
        """Extra local delivery domains must be appended via a for loop."""
        text = _read(self.TMPL)
        self.assertIn("local_domains", text)
        self.assertIn("for _d in", text)

    def test_relay_domains_conditional(self):
        """relay_domains line only emitted when list is non-empty."""
        text = _read(self.TMPL)
        self.assertIn("relay_domains", text)
        # Must be inside a conditional block
        self.assertIn("if mailserver.relay_domains", text)

    def test_relay_domains_uses_join(self):
        """relay_domains value is comma-joined list."""
        text = _read(self.TMPL)
        self.assertIn("relay_domains | join", text)

    def test_mydestination_before_relay_domains(self):
        """mydestination must appear before relay_domains in the config."""
        text = _read(self.TMPL)
        dest_pos  = text.index("mydestination")
        relay_pos = text.index("relay_domains")
        self.assertLess(dest_pos, relay_pos)


class TestMailserverDefaults(unittest.TestCase):

    DEFAULTS = "roles/mailserver/defaults/main.yml"

    def test_local_domains_key_present(self):
        self.assertIn("local_domains", _read(self.DEFAULTS))

    def test_relay_domains_key_present(self):
        self.assertIn("relay_domains", _read(self.DEFAULTS))

    def test_local_domains_defaults_to_empty(self):
        text = _read(self.DEFAULTS)
        self.assertIn("mailserver_local_domains | default([])", text)

    def test_relay_domains_defaults_to_empty(self):
        text = _read(self.DEFAULTS)
        self.assertIn("mailserver_relay_domains | default([])", text)

    def test_flat_variable_documentation_present(self):
        """Comment block documenting flat variables must be present."""
        text = _read(self.DEFAULTS)
        self.assertIn("mailserver_local_domains", text)
        self.assertIn("mailserver_relay_domains", text)
        self.assertIn("mailserver_ports", text)
        self.assertIn("mailserver_open_ports", text)

    def test_open_ports_default_present(self):
        text = _read(self.DEFAULTS)
        self.assertIn("open_ports", text)
        self.assertIn("mailserver_ports | default(mailserver_open_ports | default([25, 587, 143, 465]))", text)


class TestMailserverFirewallTemplate(unittest.TestCase):

    TEMPLATE = "roles/mailserver/templates/40-mailserver.nft.j2"
    PF_TEMPLATE = "roles/firewall/templates/pf.conf.j2"

    def test_nft_firewall_uses_open_ports_variable(self):
        text = _read(self.TEMPLATE)
        self.assertIn("mailserver_ports", text)
        self.assertIn("for _port in", text)

    def test_nft_firewall_default_port_list_omits_stale_imaps(self):
        text = _read(self.TEMPLATE)
        self.assertIn("default([25, 587, 143, 465])", text)
        self.assertNotIn("default([25, 587, 465, 993])", text)

    def test_pf_firewall_uses_open_ports_variable(self):
        text = _read(self.PF_TEMPLATE)
        self.assertIn("mailserver_ports", text)
        self.assertIn("join(', ')", text)
        self.assertIn("mailserver_ports | default(mailserver.open_ports | default([25, 587, 143, 465]))", text)


if __name__ == "__main__":
    unittest.main()
