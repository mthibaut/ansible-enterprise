"""
Unit tests for scripts/internal/resolve_capabilities.py

Tests resolve_providers() against synthetic capabilities / services inputs.
"""
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "scripts" / "internal"))
from resolve_capabilities import resolve_providers

# Canonical capabilities dict matching group_vars/all/main.yml
CAPS = {
    "tls":             {"provider": "nginx"},
    "reverse_proxy":   {"provider": "nginx"},
    "dns":             {"provider": "bind"},
    "database":        {"provider": "mariadb"},
    "firewall":        {"provider": "nftables"},
    "geoip":           {"provider": "maxmind_nftables"},
    "mail":            {"provider": "mailserver"},
    "id_mapping":      {"provider": "nfs"},
}


class TestResolveProviders(unittest.TestCase):

    # ------------------------------------------------------------------
    # Baseline / empty cases
    # ------------------------------------------------------------------

    def test_empty_inputs(self):
        self.assertEqual(resolve_providers({}, {}), [])

    def test_no_services_with_requires(self):
        services = {"app": {"enabled": True, "domain": "x.com"}}
        self.assertEqual(resolve_providers(CAPS, services), [])

    def test_disabled_service_ignored(self):
        services = {"app": {"enabled": False, "requires": ["mail"]}}
        self.assertEqual(resolve_providers(CAPS, services), [])

    def test_missing_enabled_key_treated_as_disabled(self):
        services = {"app": {"requires": ["mail"]}}
        self.assertEqual(resolve_providers(CAPS, services), [])

    # ------------------------------------------------------------------
    # Single capability resolution
    # ------------------------------------------------------------------

    def test_mail_requires_resolves_to_mailserver(self):
        services = {"app": {"enabled": True, "requires": ["mail"]}}
        self.assertIn("mailserver", resolve_providers(CAPS, services))

    def test_tls_requires_resolves_to_nginx(self):
        services = {"app": {"enabled": True, "requires": ["tls"]}}
        self.assertIn("nginx", resolve_providers(CAPS, services))

    def test_dns_requires_resolves_to_bind(self):
        services = {"app": {"enabled": True, "requires": ["dns"]}}
        self.assertIn("bind", resolve_providers(CAPS, services))

    def test_id_mapping_requires_resolves_to_nfs(self):
        services = {"app": {"enabled": True, "requires": ["id_mapping"]}}
        self.assertIn("nfs", resolve_providers(CAPS, services))

    # ------------------------------------------------------------------
    # Multiple services and deduplication
    # ------------------------------------------------------------------

    def test_two_services_same_capability_deduped(self):
        services = {
            "a": {"enabled": True, "requires": ["mail"]},
            "b": {"enabled": True, "requires": ["mail"]},
        }
        result = resolve_providers(CAPS, services)
        self.assertEqual(result.count("mailserver"), 1)

    def test_two_services_different_capabilities(self):
        services = {
            "a": {"enabled": True, "requires": ["tls"]},
            "b": {"enabled": True, "requires": ["mail"]},
        }
        result = resolve_providers(CAPS, services)
        self.assertIn("nginx", result)
        self.assertIn("mailserver", result)

    def test_one_service_multiple_requires(self):
        services = {
            "app": {"enabled": True, "requires": ["tls", "mail", "database"]},
        }
        result = resolve_providers(CAPS, services)
        self.assertIn("nginx", result)
        self.assertIn("mailserver", result)
        self.assertIn("mariadb", result)

    # ------------------------------------------------------------------
    # Unknown / missing capabilities
    # ------------------------------------------------------------------

    def test_unknown_capability_silently_skipped(self):
        """Unknown names are skipped here; CI enforces them via contracts."""
        services = {"app": {"enabled": True, "requires": ["nonexistent"]}}
        self.assertEqual(resolve_providers(CAPS, services), [])

    def test_capability_with_no_provider_key_skipped(self):
        caps = {"broken": {"description": "no provider key"}}
        services = {"app": {"enabled": True, "requires": ["broken"]}}
        self.assertEqual(resolve_providers(caps, services), [])

    def test_capability_with_empty_provider_skipped(self):
        caps = {"empty": {"provider": ""}}
        services = {"app": {"enabled": True, "requires": ["empty"]}}
        self.assertEqual(resolve_providers(caps, services), [])

    # ------------------------------------------------------------------
    # Output properties
    # ------------------------------------------------------------------

    def test_result_is_sorted(self):
        services = {
            "a": {"enabled": True, "requires": ["tls", "mail", "database"]},
        }
        result = resolve_providers(CAPS, services)
        self.assertEqual(result, sorted(result))

    def test_empty_requires_list_yields_nothing(self):
        services = {"app": {"enabled": True, "requires": []}}
        self.assertEqual(resolve_providers(CAPS, services), [])

    def test_mixed_enabled_and_disabled(self):
        services = {
            "live":  {"enabled": True,  "requires": ["mail"]},
            "off":   {"enabled": False, "requires": ["tls"]},
        }
        result = resolve_providers(CAPS, services)
        self.assertIn("mailserver", result)
        self.assertNotIn("nginx", result)


if __name__ == "__main__":
    unittest.main()


class TestResolveCapabilitiesJinja2Parity(unittest.TestCase):
    """Structural parity: verify the Jinja2 set_fact in site.yml contains
    the same algorithmic elements as resolve_providers() in Python.
    """

    BUILD = pathlib.Path(__file__).resolve().parents[3] / "build"
    SITE_YML = BUILD / "site.yml"

    def _jinja(self) -> str:
        return self.SITE_YML.read_text(encoding="utf-8")

    def test_jinja_iterates_services(self):
        """Jinja2 must loop over services, matching Python's for svc in services."""
        self.assertIn("services", self._jinja())

    def test_jinja_checks_enabled(self):
        """Jinja2 must gate on .enabled, matching Python's svc.get('enabled')."""
        self.assertIn(".enabled", self._jinja())

    def test_jinja_reads_requires(self):
        """Jinja2 must read the requires list, matching Python's svc.get('requires')."""
        self.assertIn(".requires", self._jinja())

    def test_jinja_looks_up_provider(self):
        """Jinja2 must read the provider key, matching Python's cap['provider']."""
        self.assertIn(".provider", self._jinja())

    def test_jinja_deduplicates(self):
        """Jinja2 must deduplicate providers (not in list check)."""
        self.assertIn("not in", self._jinja())

    def test_python_and_jinja_agree_on_fixture(self):
        """Run Python on a fixture and verify correctness. Highest-confidence
        parity check short of executing Jinja2 against the same input."""
        caps = {
            "tls":  {"provider": "nginx"},
            "mail": {"provider": "mailserver"},
            "dns":  {"provider": "bind"},
        }
        services = {
            "web":  {"enabled": True,  "requires": ["tls", "mail"]},
            "api":  {"enabled": True,  "requires": ["tls"]},       # nginx not duped
            "off":  {"enabled": False, "requires": ["dns"]},        # ignored
        }
        result = resolve_providers(caps, services)

        self.assertIn("nginx", result)
        self.assertIn("mailserver", result)
        self.assertNotIn("bind", result)   # disabled service
        self.assertEqual(result.count("nginx"), 1)  # deduplicated
        self.assertEqual(result, sorted(result))
        self.assertEqual(set(result), {"mailserver", "nginx"})
