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
        # Default list is now imap-conditional: [25, 587, 143, 465] when
        # imap.enabled, [25] otherwise. The full expression:
        self.assertIn(
            "mailserver_ports | default(mailserver_open_ports | "
            "default(([25, 587, 143, 465] if (mailserver_imap_enabled | "
            "default(true) | bool) else [25])))",
            text,
        )


class TestOpendkimConfTemplate(unittest.TestCase):
    """Regression: opendkim must drop privileges to the opendkim user.
    The Debian opendkim.service unit has no User= directive, so without
    UserID in opendkim.conf the daemon runs as root and refuses to load
    mail.private (owned opendkim:opendkim 0600) with
    'key data is not secure: not owned by the executing uid (0)'.
    FreeBSD's milter-opendkim port handles uid via rc.d, so UserID must
    be guarded by os_family != 'FreeBSD'."""

    TMPL = "roles/mailserver/templates/opendkim.conf.j2"

    def test_userid_directive_present(self):
        self.assertIn("UserID opendkim", _read(self.TMPL))

    def test_userid_guarded_to_non_freebsd(self):
        text = _read(self.TMPL)
        non_freebsd = text.split("ansible_facts.os_family != 'FreeBSD'")[1]
        guarded_block = non_freebsd.split("{% endif %}")[0]
        self.assertIn("UserID opendkim", guarded_block)


class TestDkimInlineMaterial(unittest.TestCase):
    """Inline DKIM key material support for host migration.
    When mailserver.dkim.private_key_pem is set, the role must install it
    with no_log instead of running opendkim-genkey, so the published
    mail._domainkey DNS TXT record stays valid across host moves."""

    DEFAULTS = "roles/mailserver/defaults/main.yml"
    TASKS    = "roles/mailserver/tasks/main.yml"

    def test_dkim_block_in_defaults(self):
        text = _read(self.DEFAULTS)
        self.assertIn("dkim:", text)
        self.assertIn("mailserver_dkim_private_key_pem", text)
        self.assertIn("mailserver_dkim_txt_record", text)

    def test_dkim_defaults_to_empty(self):
        text = _read(self.DEFAULTS)
        self.assertIn("mailserver_dkim_private_key_pem | default('')", text)
        self.assertIn("mailserver_dkim_txt_record | default('')", text)

    def test_install_inline_private_key_task_present(self):
        text = _read(self.TASKS)
        self.assertIn("Install inline DKIM private key", text)
        self.assertIn("mailserver.dkim.private_key_pem", text)

    def test_install_inline_txt_record_task_present(self):
        text = _read(self.TASKS)
        self.assertIn("Install inline DKIM public TXT record", text)
        self.assertIn("mailserver.dkim.txt_record", text)

    def test_inline_key_tasks_are_no_log(self):
        """Secret material must not leak into Ansible output (checkpoint-228 model)."""
        text = _read(self.TASKS)
        # Find the two tasks and verify each has no_log: true
        for marker in ("Install inline DKIM private key",
                       "Install inline DKIM public TXT record"):
            idx = text.index(marker)
            # Look forward up to the next "- name:" boundary for no_log: true
            tail = text[idx:]
            next_task = tail.find("\n- name:", 1)
            block = tail if next_task == -1 else tail[:next_task]
            self.assertIn("no_log: true", block,
                          f"Task '{marker}' must set no_log: true")

    def test_genkey_still_present_for_default_path(self):
        """The opendkim-genkey fallback stays so unconfigured hosts still work."""
        text = _read(self.TASKS)
        self.assertIn("opendkim-genkey", text)

    def test_inline_key_runs_before_genkey(self):
        """Inline copy must precede genkey so the creates: guard skips correctly."""
        text = _read(self.TASKS)
        inline_pos = text.index("Install inline DKIM private key")
        genkey_pos = text.index("Generate DKIM key if absent")
        self.assertLess(inline_pos, genkey_pos)

    def test_inline_copy_modes_match_chown_loop_mode(self):
        """Regression: mode declared on the inline copy tasks must match the
        mode set by the subsequent 'Set DKIM key ownership' loop. A mismatch
        causes the two tasks to fight on every run (copy resets one mode,
        chown resets the other) and breaks idempotence."""
        text = _read(self.TASKS)

        # Find the chown loop's mode
        chown_idx = text.index("Set DKIM key ownership")
        chown_block = text[chown_idx:chown_idx + 600]
        # Extract mode from a 'mode: "0NNN"' line in that block
        import re
        m = re.search(r'mode:\s*"(\d{4})"', chown_block)
        self.assertIsNotNone(m, "chown loop must declare a mode")
        chown_mode = m.group(1)

        # Both inline tasks must use the same mode
        for marker in ("Install inline DKIM private key",
                       "Install inline DKIM public TXT record"):
            idx = text.index(marker)
            tail = text[idx:]
            next_task = tail.find("\n- name:", 1)
            block = tail if next_task == -1 else tail[:next_task]
            mm = re.search(r'mode:\s*"(\d{4})"', block)
            self.assertIsNotNone(mm, f"'{marker}' must declare a mode")
            self.assertEqual(
                mm.group(1), chown_mode,
                f"'{marker}' mode {mm.group(1)} != chown loop mode {chown_mode}; "
                "the two tasks will fight every run."
            )


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


class TestImapAndDkimToggles(unittest.TestCase):
    """mailserver.imap.enabled and mailserver.dkim.enabled gate Dovecot
    and OpenDKIM independently. Backup-MX / outbound-only hosts run
    Postfix on port 25 only with imap.enabled=false; hosts that don't
    sign mail run with dkim.enabled=false."""

    DEFAULTS = "roles/mailserver/defaults/main.yml"
    TASKS    = "roles/mailserver/tasks/main.yml"
    MAIN_CF  = "roles/mailserver/templates/main.cf.j2"
    MASTER   = "roles/mailserver/templates/master.cf.j2"

    def test_defaults_expose_imap_enabled(self):
        text = _read(self.DEFAULTS)
        self.assertIn("imap:", text)
        self.assertIn("mailserver_imap_enabled | default(true)", text)

    def test_defaults_expose_dkim_enabled(self):
        text = _read(self.DEFAULTS)
        self.assertIn("mailserver_dkim_enabled | default(true)", text)

    def test_open_ports_default_drops_to_25_when_imap_off(self):
        text = _read(self.DEFAULTS)
        self.assertIn("[25, 587, 143, 465] if (mailserver_imap_enabled | default(true) | bool) else [25]", text)

    def test_dovecot_config_block_gated_on_imap_enabled(self):
        text = _read(self.TASKS)
        self.assertIn("Configure Dovecot", text)
        # The Configure Dovecot block must declare when: imap.enabled
        idx = text.index("Configure Dovecot")
        block = text[idx:idx + 400]
        self.assertIn("mailserver.imap.enabled", block)

    def test_dovecot_service_start_gated_on_imap_enabled(self):
        text = _read(self.TASKS)
        idx = text.index("Activate Dovecot service")
        block = text[idx:idx + 200]
        self.assertIn("mailserver.imap.enabled", block)

    def test_opendkim_config_block_gated_on_dkim_enabled(self):
        text = _read(self.TASKS)
        self.assertIn("Configure OpenDKIM", text)
        idx = text.index("Configure OpenDKIM")
        block = text[idx:idx + 400]
        self.assertIn("mailserver.dkim.enabled", block)

    def test_opendkim_service_start_gated_on_dkim_enabled(self):
        text = _read(self.TASKS)
        idx = text.index("Activate OpenDKIM service")
        block = text[idx:idx + 200]
        self.assertIn("mailserver.dkim.enabled", block)

    def test_dovecot_packages_appended_only_when_imap_enabled(self):
        text = _read(self.TASKS)
        idx = text.index("Append dovecot packages")
        block = text[idx:idx + 500]
        self.assertIn("mailserver.imap.enabled | default(true) | bool", block)

    def test_opendkim_packages_appended_only_when_dkim_enabled(self):
        text = _read(self.TASKS)
        idx = text.index("Append opendkim packages")
        block = text[idx:idx + 500]
        self.assertIn("mailserver.dkim.enabled | default(true) | bool", block)

    def test_main_cf_sasl_block_gated_on_imap(self):
        text = _read(self.MAIN_CF)
        self.assertIn("if mailserver.imap.enabled", text)
        # Both branches present: with-SASL and without
        self.assertIn("smtpd_sasl_type = dovecot", text)
        self.assertIn("permit_mynetworks,reject_unauth_destination", text)

    def test_main_cf_milter_block_gated_on_dkim(self):
        text = _read(self.MAIN_CF)
        self.assertIn("if mailserver.dkim.enabled", text)
        self.assertIn("smtpd_milters = inet:127.0.0.1:8891", text)

    def test_master_cf_submission_and_smtps_gated_on_imap(self):
        text = _read(self.MASTER)
        # Find where submission line lives -- must be inside imap.enabled guard
        guard_pos = text.index("if mailserver.imap.enabled")
        submission_pos = text.index("submission inet")
        smtps_pos = text.index("smtps     inet")
        endif_pos = text.index("{% endif %}", guard_pos)
        self.assertLess(guard_pos, submission_pos)
        self.assertLess(submission_pos, endif_pos)
        self.assertLess(smtps_pos, endif_pos)


if __name__ == "__main__":
    unittest.main()
