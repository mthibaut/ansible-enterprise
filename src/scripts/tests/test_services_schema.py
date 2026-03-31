"""
Unit tests for services schema validation (src/schemas/services.schema.json).

Tests the schema directly via jsonschema.validate to confirm valid and
invalid service declarations. validate_services_schema.py is a thin wrapper
around jsonschema; the schema itself is what we're testing.
"""
import json
import pathlib
import unittest

try:
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

REPO   = pathlib.Path(__file__).resolve().parents[3]
SCHEMA = json.loads((REPO / "src" / "schemas" / "services.schema.json")
                    .read_text(encoding="utf-8"))


@unittest.skipUnless(JSONSCHEMA_AVAILABLE, "jsonschema not installed")
class TestServicesSchema(unittest.TestCase):

    def _ok(self, services):
        validate(instance=services, schema=SCHEMA)

    def _fail(self, services):
        with self.assertRaises(ValidationError):
            validate(instance=services, schema=SCHEMA)

    # ── valid cases ───────────────────────────────────────────────────────────

    def test_empty_services_valid(self):
        self._ok({})

    def test_minimal_valid_service(self):
        self._ok({"app": {"enabled": True, "domain": "app.example.com", "owner": "www"}})

    def test_generic_service_with_web(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"tls": True, "expose_https": True},
            "web": {"upstream_host": "127.0.0.1", "upstream_port": 8080},
        }})

    def test_nextcloud_service_with_required_app_fields(self):
        self._ok({"nextcloud": {
            "enabled": True, "domain": "nc.example.com", "owner": "nc",
            "app": {
                "type": "nextcloud",
                "db_name": "nc", "db_user": "nc", "db_password": "x",
                "data_dir": "/data", "admin_password": "x",
            },
        }})

    def test_geoip_allowed_countries_valid(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"geoip_allowed_countries": ["BE", "NL"]},
        }})

    def test_geoip_allowlist_valid(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"geoip_allowlist": ["1.2.3.4", "10.0.0.0/8"]},
        }})

    def test_geoip_enabled_false_valid(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"geoip_enabled": False},
        }})

    def test_depends_on_valid(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "depends_on": ["db"],
        }})

    # ── invalid cases ─────────────────────────────────────────────────────────

    def test_missing_enabled_invalid(self):
        self._fail({"app": {"domain": "app.example.com", "owner": "www"}})

    def test_missing_domain_invalid(self):
        self._fail({"app": {"enabled": True, "owner": "www"}})

    def test_missing_owner_valid(self):
        """owner is optional: Docker-managed services (grafana, prometheus) omit it."""
        self._ok({"app": {"enabled": True, "domain": "app.example.com", "port": 3000}})

    def test_port_field_valid(self):
        """port: is a valid shorthand for Docker-managed services."""
        self._ok({"app": {"enabled": True, "domain": "app.example.com", "port": 9090}})

    def test_empty_domain_invalid(self):
        self._fail({"app": {"enabled": True, "domain": "", "owner": "www"}})

    def test_extra_top_level_field_invalid(self):
        self._fail({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "unknown_field": "value",
        }})

    def test_nextcloud_missing_db_name_invalid(self):
        self._fail({"nc": {
            "enabled": True, "domain": "nc.example.com", "owner": "nc",
            "app": {
                "type": "nextcloud",
                # missing db_name, db_user, db_password, data_dir, admin_password
            },
        }})

    def test_geoip_allowed_countries_wrong_length_invalid(self):
        self._fail({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"geoip_allowed_countries": ["BEL"]},  # 3 chars, not 2
        }})

    def test_web_upstream_port_out_of_range_invalid(self):
        self._fail({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "web": {"upstream_host": "127.0.0.1", "upstream_port": 99999},
        }})

    def test_web_missing_upstream_host_invalid(self):
        self._fail({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "web": {"upstream_port": 8080},
        }})

    def test_access_allowlist_valid(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {
                "expose_https": True,
                "access_allowlist": ["10.0.0.0/8", "192.168.1.10", "2001:db8::/32"],
            },
            "web": {"upstream_host": "127.0.0.1", "upstream_port": 9090},
        }})

    def test_access_allowlist_empty_valid(self):
        self._ok({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"access_allowlist": []},
        }})

    def test_access_allowlist_non_string_invalid(self):
        self._fail({"app": {
            "enabled": True, "domain": "app.example.com", "owner": "www",
            "security": {"access_allowlist": [123]},
        }})


class TestNginxDispatch(unittest.TestCase):
    """Verify render_service.yml dispatches to the correct vhost template."""

    RENDER_SERVICE = (
        pathlib.Path(__file__).resolve().parents[3]
        / "build" / "roles" / "nginx" / "tasks" / "render_service.yml"
    )

    def _dispatch_text(self):
        return self.RENDER_SERVICE.read_text(encoding="utf-8")

    def test_restricted_site_dispatched_for_access_allowlist(self):
        text = self._dispatch_text()
        self.assertIn("access_allowlist", text)
        self.assertIn("restricted_site.conf.j2", text)

    def test_restricted_site_before_client_cert(self):
        """access_allowlist branch must take priority over require_client_cert."""
        text = self._dispatch_text()
        restricted_pos = text.index("restricted_site.conf.j2")
        client_cert_pos = text.index("client_cert_site.conf.j2")
        self.assertLess(restricted_pos, client_cert_pos)

    def test_nextcloud_first_in_dispatch(self):
        text = self._dispatch_text()
        nextcloud_pos = text.index("nextcloud.conf.j2")
        restricted_pos = text.index("restricted_site.conf.j2")
        self.assertLess(nextcloud_pos, restricted_pos)

    def test_restricted_site_template_has_deny_all(self):
        tmpl = (
            pathlib.Path(__file__).resolve().parents[3]
            / "build" / "roles" / "nginx" / "templates" / "restricted_site.conf.j2"
        )
        content = tmpl.read_text(encoding="utf-8")
        self.assertIn("deny all", content)
        self.assertIn("access_allowlist", content)
        self.assertIn("allow", content)

    def test_restricted_site_template_has_proxy_pass(self):
        tmpl = (
            pathlib.Path(__file__).resolve().parents[3]
            / "build" / "roles" / "nginx" / "templates" / "restricted_site.conf.j2"
        )
        content = tmpl.read_text(encoding="utf-8")
        self.assertIn("proxy_pass", content)
        self.assertIn("upstream_host", content)
        self.assertIn("upstream_port", content)


if __name__ == "__main__":
    unittest.main()
