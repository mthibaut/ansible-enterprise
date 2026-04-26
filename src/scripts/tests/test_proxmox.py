"""
Unit tests for the generated Proxmox role backup-job integration.

Covers the API-driven backup_jobs contract:
- mthibaut.proxmox collection dependency is declared
- backup job IDs are strictly prefixed from backup_jobs_prefix + item.key
- comment defaults are generated when a job omits comment
- proxmox_api_token_secret is required when backup_jobs is non-empty
- backup job management is additive-only: no purge/delete-by-absence logic
- legacy vzdump.conf template is removed from the manifest and contracts
- legacy postfix SMTP relay tasks are gone (replaced by per-job mailto;
  full notification migration deferred to PVE notification endpoints API)
"""
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"
GENERATOR = REPO / "src" / "generate_ansible_enterprise.py"
GENERATION_CONTRACTS = REPO / "src" / "scripts" / "generation_contracts.yml"


def _read_build(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


def _read(path):
    return path.read_text(encoding="utf-8")


class TestProxmoxBackupJobs(unittest.TestCase):
    TASKS = "roles/proxmox/tasks/main.yml"
    DEFAULTS = "roles/proxmox/defaults/main.yml"

    def test_requirements_include_custom_proxmox_collection(self):
        text = _read_build("requirements.yml")
        self.assertIn("name: community.proxmox", text)
        self.assertIn("name: mthibaut.proxmox", text)

    def test_defaults_expose_api_and_backup_jobs_contract(self):
        text = _read_build(self.DEFAULTS)
        self.assertIn("proxmox_api_token_secret", text)
        self.assertIn("api:", text)
        self.assertIn("user: root@pam", text)
        self.assertIn("token_id: ansible", text)
        self.assertIn("validate_certs: true", text)
        self.assertIn("backup_jobs: {}", text)
        self.assertIn('backup_jobs_prefix: "ansible-"', text)
        self.assertIn("The role NEVER auto-deletes jobs", text)

    def test_backup_jobs_use_custom_module_from_controller(self):
        text = _read_build(self.TASKS)
        self.assertIn("mthibaut.proxmox.proxmox_backup_job:", text)
        self.assertIn("delegate_to: localhost", text)
        self.assertIn('run_once: "{{ proxmox.is_clustered | default(true) | bool }}"', text)

    def test_backup_job_id_uses_strict_prefix_and_key(self):
        text = _read_build(self.TASKS)
        self.assertIn('id: "{{ proxmox.backup_jobs_prefix | default(\'ansible-\') }}{{ item.key }}"', text)
        self.assertNotIn("item.value.id", text)
        self.assertNotIn("backup_job_id", text)

    def test_backup_job_comment_has_auto_default(self):
        text = _read_build(self.TASKS)
        self.assertIn(
            "comment: \"{{ item.value.comment | default('Managed by Ansible (proxmox role) -- do not edit in web UI') }}\"",
            text,
        )

    def test_api_token_secret_asserted_when_jobs_declared(self):
        text = _read_build(self.TASKS)
        self.assertIn("Assert proxmox_api_token_secret is set when backup_jobs declared", text)
        self.assertIn("proxmox_api_token_secret is defined", text)
        self.assertIn("proxmox_api_token_secret | length > 0", text)
        self.assertIn("proxmox.backup_jobs | default({}) | length > 0", text)

    def test_backup_jobs_are_additive_only(self):
        text = _read_build(self.TASKS)
        backup_jobs = text.split("- name: Manage Proxmox cluster backup jobs", 1)[1]
        backup_jobs = backup_jobs.split("# -- IOMMU / PCI passthrough", 1)[0]
        self.assertIn('state: "{{ item.value.state | default(\'present\') }}"', backup_jobs)
        forbidden = [
            "purge",
            "delete_missing",
            "existing_backup_jobs",
            "backup_jobs_to_delete",
            "difference(",
            "state: absent",
        ]
        for marker in forbidden:
            self.assertNotIn(marker, backup_jobs)

    def test_legacy_vzdump_template_removed(self):
        self.assertFalse((BUILD / "roles/proxmox/templates/vzdump.conf.j2").exists())

        generator = _read(GENERATOR)
        self.assertNotIn("'roles/proxmox/templates/vzdump.conf.j2'", generator)

        contracts = _read(GENERATION_CONTRACTS)
        self.assertNotIn("roles/proxmox/templates/vzdump.conf.j2", contracts)

    def test_legacy_postfix_smtp_relay_removed(self):
        """The postfix-based SMTP relay path was unused and has been removed.
        Per-job mailto on backup_jobs covers the common case; full migration
        to /cluster/notifications/endpoints API is deferred until needed."""
        defaults = _read_build(self.DEFAULTS)
        self.assertNotIn("smtp:", defaults)
        self.assertNotIn("relayhost", defaults)
        self.assertNotIn("proxmox_smtp_password", defaults)

        tasks = _read_build(self.TASKS)
        self.assertNotIn("proxmox.smtp", tasks)
        self.assertNotIn("Configure postfix relayhost", tasks)
        self.assertNotIn("postfix SASL", tasks)
        self.assertNotIn("/etc/postfix/main.cf", tasks)
        self.assertNotIn("/etc/postfix/sasl_passwd", tasks)

        handlers = _read_build("roles/proxmox/handlers/main.yml")
        self.assertNotIn("Restart postfix", handlers)


if __name__ == "__main__":
    unittest.main()
