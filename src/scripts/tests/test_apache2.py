"""
Unit tests for the apache2 role: vhost template defaults, cgi-bin support,
and directory-creation tasks.

Covers:
- DocumentRoot defaults to <web_root>/htdocs (not the bare web_root)
- web_root defaults to /var/www/<domain>
- ScriptAlias / cgi-bin block only renders when cgi_bin_enabled
- mod_cgid is enabled on Debian only when at least one service opts in
- DocumentRoot directory is always created
- cgi-bin directory is created only when cgi_bin_enabled
"""
import pathlib
import unittest

REPO  = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"


def _read(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


class TestApache2VhostTemplate(unittest.TestCase):

    TMPL = "roles/apache2/templates/apache2_vhost.conf.j2"

    def test_documentroot_defaults_to_htdocs(self):
        text = _read(self.TMPL)
        # The default expression must end with /htdocs
        self.assertIn("'/htdocs'", text)
        self.assertIn("_web_base + '/htdocs'", text)

    def test_web_root_defaults_to_var_www_domain(self):
        text = _read(self.TMPL)
        self.assertIn("'/var/www/' + _svc.value.domain", text)

    def test_documentroot_uses_resolved_variable(self):
        """DocumentRoot/Directory directives use the _docroot var, not inline default chain."""
        text = _read(self.TMPL)
        self.assertIn("DocumentRoot {{ _docroot }}", text)
        self.assertIn("<Directory {{ _docroot }}>", text)

    def test_scriptalias_gated_on_cgi_enabled(self):
        text = _read(self.TMPL)
        self.assertIn("if _cgi_enabled", text)
        self.assertIn("ScriptAlias /cgi-bin/", text)

    def test_cgi_bin_default_disabled(self):
        text = _read(self.TMPL)
        self.assertIn("cgi_bin_enabled | default(false)", text)

    def test_cgi_bin_path_defaults_under_web_base(self):
        text = _read(self.TMPL)
        self.assertIn("_web_base + '/cgi-bin/'", text)

    def test_cgi_directory_block_present_inside_guard(self):
        """The <Directory cgi-bin> block sits inside the cgi_enabled guard."""
        text = _read(self.TMPL)
        cgi_block = text.split("if _cgi_enabled")[1].split("endif")[0]
        self.assertIn("ExecCGI", cgi_block)
        self.assertIn("SetHandler cgi-script", cgi_block)


class TestApache2Tasks(unittest.TestCase):

    TASKS = "roles/apache2/tasks/main.yml"

    def test_documentroot_dir_created_unconditionally(self):
        text = _read(self.TASKS)
        self.assertIn("Ensure Apache2 DocumentRoot exists", text)
        # Default must mirror template: <web_root>/htdocs
        self.assertIn("'/htdocs'", text)

    def test_cgi_bin_dir_creation_gated(self):
        text = _read(self.TASKS)
        idx = text.index("Ensure Apache2 cgi-bin directory exists")
        # Look forward for the when: clause
        block = text[idx:idx + 600]
        self.assertIn("cgi_bin_enabled | default(false) | bool", block)

    def test_cgid_mod_enabled_only_for_opted_in_services(self):
        text = _read(self.TASKS)
        idx = text.index("Enable mod_cgid (Debian)")
        block = text[idx:idx + 500]
        self.assertIn("a2enmod cgid", block)
        self.assertIn("selectattr('value.app.cgi_bin_enabled'", block)

    def test_documentroot_dir_owned_by_service_owner(self):
        text = _read(self.TASKS)
        idx = text.index("Ensure Apache2 DocumentRoot exists")
        block = text[idx:idx + 600]
        self.assertIn("item.value.owner | default('root')", block)


if __name__ == "__main__":
    unittest.main()
