"""
Unit tests for the ssh_hardening role: per-host overrides for the
sshd config directives that previously had only auto-derived or
hardcoded values.

Covers:
- ssh_password_authentication: auto / yes / no
- ssh_permit_root_login: auto / yes / no / prohibit-password / etc.
- ssh_pubkey_authentication: yes / no override (default yes)
- ssh_allow_users: empty (auto) / explicit list override

Both the drop-in (99-ansible-enterprise.conf.j2) and the full
sshd_config.j2 carry the same overrides; both are checked.
"""
import pathlib
import unittest

REPO  = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"

DROP_IN  = "roles/ssh_hardening/templates/99-ansible-enterprise.conf.j2"
FULL_CFG = "roles/ssh_hardening/templates/sshd_config.j2"
DEFAULTS = "roles/ssh_hardening/defaults/main.yml"


def _read(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


class TestSshHardeningDefaults(unittest.TestCase):

    def test_password_auth_default_auto(self):
        self.assertIn("ssh_password_authentication: auto", _read(DEFAULTS))

    def test_permit_root_login_default_auto(self):
        self.assertIn("ssh_permit_root_login: auto", _read(DEFAULTS))

    def test_pubkey_auth_default_yes(self):
        self.assertIn("ssh_pubkey_authentication: 'yes'", _read(DEFAULTS))

    def test_allow_users_default_empty(self):
        self.assertIn("ssh_allow_users: ''", _read(DEFAULTS))


class TestPasswordAuthOverride(unittest.TestCase):
    """ssh_password_authentication must override the auto-derived value."""

    def _check(self, text):
        # auto path retained
        self.assertIn("_pw_auto", text)
        self.assertIn("admin_dev_password_hash", text)
        # explicit override path
        self.assertIn("ssh_password_authentication", text)
        self.assertIn("_pw if _pw in ['yes', 'no']", text)

    def test_drop_in(self):  self._check(_read(DROP_IN))
    def test_full_cfg(self): self._check(_read(FULL_CFG))


class TestPermitRootLoginOverride(unittest.TestCase):

    def _check(self, text):
        self.assertIn("ssh_permit_root_login", text)
        self.assertIn("'prohibit-password'", text)
        # all five legal explicit values are accepted
        for v in ("'yes'", "'no'", "'prohibit-password'",
                  "'forced-commands-only'", "'without-password'"):
            self.assertIn(v, text, f"PermitRootLogin override missing value {v}")

    def test_drop_in(self):  self._check(_read(DROP_IN))
    def test_full_cfg(self): self._check(_read(FULL_CFG))


class TestPubkeyAuthOverride(unittest.TestCase):

    def _check(self, text):
        self.assertIn("ssh_pubkey_authentication | default('yes')", text)

    def test_drop_in(self):  self._check(_read(DROP_IN))
    def test_full_cfg(self): self._check(_read(FULL_CFG))


class TestAllowUsersOverride(unittest.TestCase):

    def _check(self, text):
        # explicit override
        self.assertIn("ssh_allow_users", text)
        self.assertIn("_allow if _allow | length > 0", text)
        # auto path keeps root + admin users
        self.assertIn("'root ' ~", text)
        self.assertIn("admin_users", text)

    def test_drop_in(self):  self._check(_read(DROP_IN))
    def test_full_cfg(self): self._check(_read(FULL_CFG))


if __name__ == "__main__":
    unittest.main()
