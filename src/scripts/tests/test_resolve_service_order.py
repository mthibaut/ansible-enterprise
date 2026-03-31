"""
Unit tests for scripts/resolve_service_order.py

Tests the resolve_order() function directly against synthetic services dicts.
"""
import sys
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "scripts"))
from resolve_service_order import resolve_order


class TestResolveOrder(unittest.TestCase):

    def test_empty_services(self):
        self.assertEqual(resolve_order({}), [])

    def test_single_service_no_deps(self):
        svc = {"app": {"enabled": True}}
        self.assertEqual(resolve_order(svc), ["app"])

    def test_multiple_services_no_deps_sorted(self):
        svc = {"zebra": {}, "alpha": {}, "middle": {}}
        result = resolve_order(svc)
        self.assertEqual(result, sorted(result))
        self.assertEqual(set(result), {"zebra", "alpha", "middle"})

    def test_simple_dependency(self):
        svc = {
            "db":  {"depends_on": []},
            "app": {"depends_on": ["db"]},
        }
        result = resolve_order(svc)
        self.assertLess(result.index("db"), result.index("app"))

    def test_chain_dependency(self):
        svc = {
            "a": {"depends_on": []},
            "b": {"depends_on": ["a"]},
            "c": {"depends_on": ["b"]},
        }
        result = resolve_order(svc)
        self.assertLess(result.index("a"), result.index("b"))
        self.assertLess(result.index("b"), result.index("c"))

    def test_diamond_dependency(self):
        svc = {
            "base":   {"depends_on": []},
            "left":   {"depends_on": ["base"]},
            "right":  {"depends_on": ["base"]},
            "top":    {"depends_on": ["left", "right"]},
        }
        result = resolve_order(svc)
        self.assertLess(result.index("base"), result.index("left"))
        self.assertLess(result.index("base"), result.index("right"))
        self.assertLess(result.index("left"), result.index("top"))
        self.assertLess(result.index("right"), result.index("top"))

    def test_dependency_on_unknown_service_ignored(self):
        """depends_on references to services not in the dict are silently ignored."""
        svc = {"app": {"depends_on": ["nonexistent"]}}
        result = resolve_order(svc)
        self.assertEqual(result, ["app"])

    def test_cycle_raises_systemexit(self):
        svc = {
            "a": {"depends_on": ["b"]},
            "b": {"depends_on": ["a"]},
        }
        with self.assertRaises(SystemExit):
            resolve_order(svc)

    def test_three_way_cycle_raises_systemexit(self):
        svc = {
            "a": {"depends_on": ["c"]},
            "b": {"depends_on": ["a"]},
            "c": {"depends_on": ["b"]},
        }
        with self.assertRaises(SystemExit):
            resolve_order(svc)

    def test_all_services_present_in_result(self):
        svc = {"x": {}, "y": {"depends_on": ["x"]}, "z": {}}
        result = resolve_order(svc)
        self.assertEqual(set(result), {"x", "y", "z"})


if __name__ == "__main__":
    unittest.main()
