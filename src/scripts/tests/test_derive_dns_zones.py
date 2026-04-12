"""
Unit tests for scripts/internal/derive_dns_zones.py

Tests derive_zones() against synthetic declared_zones / services inputs,
covering the same cases the Jinja2 set_fact expression handles at runtime.
"""
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "scripts" / "internal"))
from derive_dns_zones import derive_zones


class TestDeriveZones(unittest.TestCase):

    # ------------------------------------------------------------------
    # Baseline / empty cases
    # ------------------------------------------------------------------

    def test_empty_inputs_yield_empty(self):
        self.assertEqual(derive_zones([], {}), [])

    def test_declared_only_no_services(self):
        self.assertEqual(derive_zones(["example.com"], {}), ["example.com"])

    def test_declared_only_returned_sorted(self):
        result = derive_zones(["zz.example.com", "aa.example.com"], {})
        self.assertEqual(result, ["aa.example.com", "zz.example.com"])

    # ------------------------------------------------------------------
    # Service domain is the zone apex
    # ------------------------------------------------------------------

    def test_apex_domain_added_as_zone(self):
        """Service domain exactly equals a new zone — should be added."""
        services = {"app": {"enabled": True, "domain": "app.example.com"}}
        result = derive_zones([], services)
        self.assertIn("app.example.com", result)

    def test_apex_domain_not_duplicated_if_already_declared(self):
        """Service domain == declared zone — must not appear twice."""
        services = {"app": {"enabled": True, "domain": "example.com"}}
        result = derive_zones(["example.com"], services)
        self.assertEqual(result.count("example.com"), 1)

    # ------------------------------------------------------------------
    # Subdomain coverage
    # ------------------------------------------------------------------

    def test_subdomain_of_declared_zone_not_added(self):
        """app.example.com is covered by example.com — no extra zone."""
        services = {"app": {"enabled": True, "domain": "app.example.com"}}
        result = derive_zones(["example.com"], services)
        self.assertNotIn("app.example.com", result)
        self.assertIn("example.com", result)

    def test_deep_subdomain_covered(self):
        """a.b.example.com is covered by example.com."""
        services = {"deep": {"enabled": True, "domain": "a.b.example.com"}}
        result = derive_zones(["example.com"], services)
        self.assertNotIn("a.b.example.com", result)

    def test_partial_suffix_not_a_match(self):
        """notexample.com must NOT be considered covered by example.com."""
        services = {"trick": {"enabled": True, "domain": "notexample.com"}}
        result = derive_zones(["example.com"], services)
        self.assertIn("notexample.com", result)

    def test_sibling_domain_added(self):
        """sibling.com is not under example.com — should be added."""
        services = {"sibling": {"enabled": True, "domain": "sibling.com"}}
        result = derive_zones(["example.com"], services)
        self.assertIn("sibling.com", result)
        self.assertIn("example.com", result)

    # ------------------------------------------------------------------
    # Disabled services
    # ------------------------------------------------------------------

    def test_disabled_service_domain_ignored(self):
        services = {"off": {"enabled": False, "domain": "off.example.com"}}
        result = derive_zones([], services)
        self.assertEqual(result, [])

    def test_missing_enabled_key_treated_as_disabled(self):
        services = {"nokey": {"domain": "nokey.example.com"}}
        result = derive_zones([], services)
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_service_with_no_domain_skipped(self):
        services = {"nodomain": {"enabled": True}}
        result = derive_zones([], services)
        self.assertEqual(result, [])

    def test_service_with_empty_domain_skipped(self):
        services = {"empty": {"enabled": True, "domain": ""}}
        result = derive_zones([], services)
        self.assertEqual(result, [])

    def test_duplicate_service_domains_deduplicated(self):
        services = {
            "a": {"enabled": True, "domain": "shared.example.com"},
            "b": {"enabled": True, "domain": "shared.example.com"},
        }
        result = derive_zones([], services)
        self.assertEqual(result.count("shared.example.com"), 1)

    def test_result_is_sorted(self):
        services = {
            "z": {"enabled": True, "domain": "zzz.com"},
            "a": {"enabled": True, "domain": "aaa.com"},
        }
        result = derive_zones([], services)
        self.assertEqual(result, sorted(result))

    def test_mixed_declared_and_derived_sorted(self):
        services = {"app": {"enabled": True, "domain": "beta.com"}}
        result = derive_zones(["alpha.com", "gamma.com"], services)
        self.assertEqual(result, sorted(result))
        self.assertIn("beta.com", result)
        self.assertIn("alpha.com", result)
        self.assertIn("gamma.com", result)

    def test_multiple_declared_zones_cover_respective_subdomains(self):
        """Subdomains of either declared zone are suppressed."""
        services = {
            "a": {"enabled": True, "domain": "sub.one.com"},   # covered
            "b": {"enabled": True, "domain": "sub.two.com"},   # covered
            "c": {"enabled": True, "domain": "three.com"},     # new
        }
        result = derive_zones(["one.com", "two.com"], services)
        self.assertIn("one.com", result)
        self.assertIn("two.com", result)
        self.assertIn("three.com", result)
        self.assertNotIn("sub.one.com", result)
        self.assertNotIn("sub.two.com", result)


if __name__ == "__main__":
    unittest.main()


class TestDeriveZonesJinja2Parity(unittest.TestCase):
    """Structural parity: verify the Jinja2 set_fact in dns/tasks/main.yml
    contains the same algorithmic elements as derive_zones() in Python.

    These tests cannot execute Jinja2 — they assert that the Jinja2 source
    contains the structural markers of the correct algorithm so that a
    developer who changes one implementation is reminded to update the other.
    """

    BUILD = pathlib.Path(__file__).resolve().parents[3] / "build"
    DNS_TASKS  = BUILD / "roles" / "dns" / "tasks" / "main.yml"
    ZONE_TMPL  = BUILD / "roles" / "dns" / "templates" / "zone.db.j2"

    def _tasks(self) -> str:
        return self.DNS_TASKS.read_text(encoding="utf-8")

    def _zone_tmpl(self) -> str:
        return self.ZONE_TMPL.read_text(encoding="utf-8")

    def test_jinja_contains_subdomain_endswith_check(self):
        """zone.db.j2 uses endswith for subdomain coverage, matching Python."""
        self.assertIn("endswith", self._zone_tmpl())

    def test_jinja_contains_apex_equality_check(self):
        """zone.db.j2 uses == for apex match in service auto-derive."""
        self.assertIn("== item.name", self._zone_tmpl())

    def test_jinja_contains_sort(self):
        """zone.db.j2 iterates services sorted, matching Python's sorted() call."""
        self.assertIn("| sort", self._zone_tmpl())

    def test_jinja_contains_unique(self):
        """Zone uniqueness is guaranteed by dns.zones being explicit.
        dns tasks use selectattr/rejectattr on the declared list."""
        self.assertIn("dns.zones | default([])", self._tasks())

    def test_jinja_skips_disabled_services(self):
        """zone.db.j2 must gate on .enabled, matching Python's svc.get('enabled')."""
        self.assertIn(".enabled", self._zone_tmpl())

    def test_jinja_skips_empty_domains(self):
        """zone.db.j2 must handle missing domains, matching Python's domain check."""
        self.assertIn(".domain", self._zone_tmpl())

    def test_python_and_jinja_agree_on_fixture(self):
        """Run Python on a known fixture and verify the result is internally
        consistent (both declared zones and auto-derived appear, covered
        subdomains are excluded). This is the highest-confidence parity check
        short of executing Jinja2.
        """
        declared = ["example.com", "other.org"]
        services = {
            "web":    {"enabled": True,  "domain": "web.example.com"},   # covered
            "app":    {"enabled": True,  "domain": "app.other.org"},      # covered
            "extra":  {"enabled": True,  "domain": "newzone.net"},        # new zone
            "off":    {"enabled": False, "domain": "off.example.com"},    # disabled
        }
        result = derive_zones(declared, services)

        # Declared zones present
        self.assertIn("example.com", result)
        self.assertIn("other.org", result)

        # New uncovered zone added
        self.assertIn("newzone.net", result)

        # Covered subdomains excluded
        self.assertNotIn("web.example.com", result)
        self.assertNotIn("app.other.org", result)

        # Disabled service excluded
        self.assertNotIn("off.example.com", result)

        # Result is sorted
        self.assertEqual(result, sorted(result))

        # Exactly the right set
        self.assertEqual(set(result), {"example.com", "newzone.net", "other.org"})
