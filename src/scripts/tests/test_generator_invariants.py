"""
Regression tests for generator invariants established during the
2026-04-23/24 session. Every assertion here corresponds to a bug that was
found in production without a test catching it.

Coverage:
- host_locked safety guard present in all 5 entry playbooks
- state: started tasks skip under --check (not ansible_check_mode)
- state: restarted/reloaded tasks skip under --check
- Deploy <x> nftables drop-in tasks gated on firewall_enabled
- WireGuard include_tasks loop hides private_key via loop_control.label
- ssh_hardening _admin_primary_groups is check-mode safe
- mailserver_masquerade_domains is a list, emitted into postfix masquerade_domains
- /etc/environment managed via blockinfile, not copy
- ansible.cfg emitted into build/ with inject_facts_as_vars=False
"""
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"


def _read(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# host_locked safety guard on all entry playbooks
# ---------------------------------------------------------------------------

class TestHostLockedGuard(unittest.TestCase):
    """Legacy hosts with host_locked=true must be skipped cleanly."""

    PLAYBOOKS = [
        "site.yml",
        "infra.yml",
        "lxc_bootstrap.yml",
        "bootstrap.yml",
        "lxc_export.yml",
    ]

    def test_each_playbook_has_end_host_guard(self):
        for pb in self.PLAYBOOKS:
            text = _read(pb)
            self.assertIn(
                "meta: end_host", text,
                msg=f"{pb} missing meta: end_host lockdown guard",
            )
            self.assertIn(
                "host_locked | default(false) | bool", text,
                msg=f"{pb} end_host not gated on host_locked",
            )

    def test_each_playbook_announces_lockdown(self):
        for pb in self.PLAYBOOKS:
            text = _read(pb)
            self.assertIn(
                "Announce host lockdown", text,
                msg=f"{pb} missing debug announcement for locked hosts",
            )


# ---------------------------------------------------------------------------
# check-mode guards on service state-changing tasks
# ---------------------------------------------------------------------------

def _task_bodies_containing(rel_path, needle):
    """Yield (start_line_idx, body_lines) for every top-level task dict
    under tasks/handlers whose body contains `needle`."""
    text = _read(rel_path)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == needle:
            # walk backward to `- name:` with indent <= this line's indent
            indent = len(line) - len(line.lstrip())
            start = None
            for j in range(i - 1, -1, -1):
                if not lines[j].strip():
                    continue
                li = len(lines[j]) - len(lines[j].lstrip())
                if li <= indent - 2 and lines[j].lstrip().startswith("- name:"):
                    start = j
                    break
            if start is None:
                continue
            # walk forward to next task or empty+dedent
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if not lines[j].strip():
                    continue
                li = len(lines[j]) - len(lines[j].lstrip())
                if li <= indent - 2 and lines[j].lstrip().startswith("- "):
                    end = j
                    break
            yield start, lines[start:end]


def _all_role_task_files():
    return sorted((BUILD / "roles").rglob("tasks/*.yml")) \
         + sorted((BUILD / "roles").rglob("handlers/*.yml"))


class TestCheckModeGuards(unittest.TestCase):
    """Starting/restarting/reloading a service whose unit file does not yet
    exist fails in --check. All such tasks must carry `not ansible_check_mode`
    in their when: list."""

    STATE_LINES = ("state: started", "state: restarted", "state: reloaded")

    def test_service_state_changes_are_check_mode_safe(self):
        offenders = []
        for path in _all_role_task_files():
            rel = path.relative_to(BUILD).as_posix()
            for needle in self.STATE_LINES:
                for start, body in _task_bodies_containing(rel, needle):
                    body_text = "\n".join(body)
                    if "not ansible_check_mode" not in body_text:
                        # extract name for readable failure message
                        name_line = body[0].strip()
                        offenders.append(f"{rel}:{start+1} {name_line} [{needle}]")
        self.assertFalse(
            offenders,
            msg="tasks missing `not ansible_check_mode` guard:\n  "
                + "\n  ".join(offenders),
        )


# ---------------------------------------------------------------------------
# nftables drop-ins gated on firewall_enabled
# ---------------------------------------------------------------------------

class TestNftablesDropInGuard(unittest.TestCase):
    """A role that drops an nftables snippet into /etc/nftables.d/ must first
    check firewall_enabled; otherwise the task fails on hosts where the
    firewall role was skipped (dir doesn't exist)."""

    def test_every_nftables_drop_in_is_guarded(self):
        offenders = []
        for path in _all_role_task_files():
            text = path.read_text(encoding="utf-8")
            if "/etc/nftables.d/" not in text:
                continue
            rel = path.relative_to(BUILD).as_posix()
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if "Deploy " not in line or "nftables drop-in" not in line:
                    continue
                # Window: this task through next task (at most 25 lines)
                window = "\n".join(lines[i:i + 25])
                if "firewall_enabled" not in window:
                    offenders.append(f"{rel}:{i+1} {line.strip()}")
        self.assertFalse(
            offenders,
            msg="nftables drop-ins missing firewall_enabled guard:\n  "
                + "\n  ".join(offenders),
        )


# ---------------------------------------------------------------------------
# WireGuard loop hides private_key
# ---------------------------------------------------------------------------

class TestWireguardLoopSecretHiding(unittest.TestCase):
    """The include_tasks loop for WireGuard instances iterates items whose
    dicts contain `private_key`. Without a loop_control.label, the `included:`
    banner dumps the full item (secret) to the log."""

    TASKS = "roles/wireguard/tasks/main.yml"

    def test_configure_instances_has_safe_label(self):
        text = _read(self.TASKS)
        m = re.search(
            r"- name: Configure WireGuard instances.*?(?=\n- name:|\Z)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m, "Configure WireGuard instances task missing")
        task = m.group(0)
        self.assertIn("loop_control:", task)
        self.assertIn('label: "{{ _inst.name }}"', task)


# ---------------------------------------------------------------------------
# ssh_hardening admin primary groups check-mode safety
# ---------------------------------------------------------------------------

class TestAdminPrimaryGroupsLookup(unittest.TestCase):
    """The `id -gn <user>` task must run in --check mode (read-only command)
    and tolerate failure (user may not exist yet on fresh hosts). The
    downstream set_fact must skip empty stdout to avoid poisoning the map
    with empty-string groups."""

    TASKS = "roles/ssh_hardening/tasks/main.yml"

    def test_resolve_primary_groups_runs_in_check_mode(self):
        text = _read(self.TASKS)
        m = re.search(
            r"- name: Resolve admin users primary groups.*?(?=\n- name:|\Z)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m, "Resolve admin users primary groups task missing")
        task = m.group(0)
        self.assertIn("check_mode: false", task)
        self.assertIn("failed_when: false", task)

    def test_build_primary_groups_map_skips_empty_stdout(self):
        text = _read(self.TASKS)
        m = re.search(
            r"- name: Build admin user primary group map.*?(?=\n- name:|\Z)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m, "Build admin user primary group map task missing")
        task = m.group(0)
        self.assertIn("stdout | default('') | trim", task)
        self.assertIn("length > 0", task)


# ---------------------------------------------------------------------------
# mailserver_masquerade_domains is a list
# ---------------------------------------------------------------------------

class TestMasqueradeDomainsList(unittest.TestCase):
    """Postfix masquerade_domains is a list. The ansible var must match."""

    DEFAULTS = "roles/mailserver/defaults/main.yml"
    GENERIC = "roles/mailserver/templates/generic.j2"
    MAINCF = "roles/mailserver/templates/main.cf.j2"

    def test_defaults_declare_list(self):
        text = _read(self.DEFAULTS)
        self.assertIn(
            'masquerade_domains: "{{ mailserver_masquerade_domains | default([]) }}"',
            text,
        )
        # Ensure the old singular scalar is fully gone.
        self.assertNotIn("mailserver_masquerade_domain ", text)
        self.assertNotIn("masquerade_domain: \"", text)

    def test_generic_uses_first_list_entry(self):
        text = _read(self.GENERIC)
        self.assertIn("mailserver.masquerade_domains", text)
        self.assertIn("first", text)
        # Singular reference should be gone.
        self.assertNotIn("mailserver.masquerade_domain }}", text)

    def test_main_cf_emits_postfix_directive(self):
        text = _read(self.MAINCF)
        self.assertIn("masquerade_domains =", text)
        self.assertIn("mailserver.masquerade_domains | join(', ')", text)


# ---------------------------------------------------------------------------
# /etc/environment managed non-destructively
# ---------------------------------------------------------------------------

class TestHostEnvironmentBlockinfile(unittest.TestCase):
    """/etc/environment must be managed with blockinfile (preserving existing
    content) rather than copy (which clobbers it)."""

    SITE = "site.yml"
    MARKER = "# {mark} ANSIBLE MANAGED BLOCK - ansible-enterprise host_environment"

    def test_uses_blockinfile(self):
        text = _read(self.SITE)
        self.assertIn("blockinfile:", text)
        self.assertIn(self.MARKER, text)
        # path: /etc/environment should not appear under a copy: task
        copy_env = re.search(
            r"- name:[^\n]*\n\s+copy:\s*\n[^-]*dest: /etc/environment",
            text,
        )
        self.assertIsNone(
            copy_env,
            msg="/etc/environment should not be written via copy: (would clobber)",
        )

    def test_block_removed_when_unset(self):
        text = _read(self.SITE)
        # blockinfile state should be conditional on host_environment length.
        self.assertIn(
            "state: \"{{ 'present' if host_environment | default({}) | length > 0 else 'absent' }}\"",
            text,
        )

    def test_interactive_shell_exports_written_for_linux_and_freebsd(self):
        text = _read(self.SITE)
        self.assertIn("Set host environment for interactive shells", text)
        self.assertIn("dest: /etc/profile.d/ansible-enterprise.sh", text)
        self.assertIn("Set host environment for interactive shells (FreeBSD)", text)
        self.assertIn("dest: /usr/local/etc/profile.d/ansible-enterprise.sh", text)

    def test_interactive_shell_exports_removed_when_host_environment_unset(self):
        text = _read(self.SITE)
        self.assertIn("Remove host environment when unset", text)
        self.assertIn("- /etc/profile.d/ansible-enterprise.sh", text)
        self.assertIn("- /usr/local/etc/profile.d/ansible-enterprise.sh", text)
        self.assertIn("when: host_environment | default({}) | length == 0", text)


# ---------------------------------------------------------------------------
# ansible.cfg emitted into build/
# ---------------------------------------------------------------------------

class TestAnsibleCfgInBuild(unittest.TestCase):
    """ansible-playbook runs from build/, so ansible.cfg must live there
    (Ansible does not walk parents). inject_facts_as_vars must be False to
    prevent service_facts' `services` from shadowing the project var."""

    def test_build_ansible_cfg_exists(self):
        path = BUILD / "ansible.cfg"
        self.assertTrue(path.exists(), f"{path} missing — ansible won't load config")

    def test_inject_facts_as_vars_disabled(self):
        text = (BUILD / "ansible.cfg").read_text(encoding="utf-8")
        self.assertIn("inject_facts_as_vars = False", text)

    def test_parallel_execution_defaults_present(self):
        text = (BUILD / "ansible.cfg").read_text(encoding="utf-8")
        self.assertIn("forks = 20", text)
        self.assertIn("strategy = free", text)

    def test_no_stale_repo_root_cfg(self):
        stale = REPO / "ansible.cfg"
        self.assertFalse(
            stale.exists(),
            msg=f"stale {stale} shadows build/ansible.cfg when run from repo root",
        )


if __name__ == "__main__":
    unittest.main()
