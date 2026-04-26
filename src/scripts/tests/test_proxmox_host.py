"""
Unit tests for the generated proxmox_host role (Linux host preparation
for Proxmox VE: apt repos, nag removal, extra packages, IOMMU/vfio).

The proxmox_host role exists as the SSH-based companion to the API-only
proxmox role (checkpoint-234 split). It owns everything that requires
running on the PVE node itself; cluster-config concerns belong in the
separate proxmox role.
"""
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
BUILD = REPO / "build"
GENERATION_CONTRACTS = REPO / "src" / "scripts" / "generation_contracts.yml"


def _read_build(rel):
    return (BUILD / rel).read_text(encoding="utf-8")


def _read(path):
    return path.read_text(encoding="utf-8")


class TestProxmoxHostRole(unittest.TestCase):
    DEFAULTS = "roles/proxmox_host/defaults/main.yml"
    HANDLERS = "roles/proxmox_host/handlers/main.yml"
    TASKS = "roles/proxmox_host/tasks/main.yml"

    def test_role_files_exist(self):
        for rel in (self.DEFAULTS, self.HANDLERS, self.TASKS):
            self.assertTrue((BUILD / rel).exists(), f"missing {rel}")

    def test_defaults_use_proxmox_host_namespace(self):
        text = _read_build(self.DEFAULTS)
        self.assertIn("proxmox_host:", text)
        self.assertIn("enabled: false", text)
        self.assertIn("repo: no_subscription", text)
        self.assertIn("remove_nag: true", text)
        self.assertIn("extra_packages: []", text)
        self.assertIn("iommu:", text)
        self.assertIn("cpu_vendor: intel", text)

    def test_defaults_have_no_cluster_api_keys(self):
        """Cluster API config (api auth, backup_jobs) belongs to the
        separate proxmox role."""
        text = _read_build(self.DEFAULTS)
        for marker in ["api:", "backup_jobs", "is_clustered", "proxmox_api_token_secret"]:
            self.assertNotIn(marker, text, f"cluster-API key leaked into proxmox_host: {marker!r}")

    def test_handlers_cover_apt_pveproxy_grub(self):
        text = _read_build(self.HANDLERS)
        self.assertIn("Update apt cache", text)
        self.assertIn("Restart pveproxy", text)
        self.assertIn("Update GRUB", text)

    def test_tasks_have_debian_assertion(self):
        text = _read_build(self.TASKS)
        self.assertIn("ansible_facts.os_family == 'Debian'", text)
        self.assertIn("proxmox_host role only supports Debian", text)

    def test_tasks_use_proxmox_host_namespace_throughout(self):
        text = _read_build(self.TASKS)
        # Should use proxmox_host.* not proxmox.*
        self.assertIn("proxmox_host.repo", text)
        self.assertIn("proxmox_host.remove_nag", text)
        self.assertIn("proxmox_host.extra_packages", text)
        self.assertIn("proxmox_host.iommu", text)
        self.assertNotIn("proxmox.repo", text)
        self.assertNotIn("proxmox.remove_nag", text)
        self.assertNotIn("proxmox.extra_packages", text)
        self.assertNotIn("proxmox.iommu", text)

    def test_tasks_cover_repo_nag_packages_iommu(self):
        text = _read_build(self.TASKS)
        self.assertIn("pve-no-subscription", text)
        self.assertIn("pve-enterprise", text)
        self.assertIn("Remove subscription nag from web UI", text)
        self.assertIn("Install extra Proxmox packages", text)
        self.assertIn("Enable IOMMU in GRUB", text)
        self.assertIn("Load vfio modules", text)
        self.assertIn("intel_iommu=on", text)
        self.assertIn("amd_iommu=on", text)

    def test_tasks_have_no_cluster_api_calls(self):
        """The proxmox_host role must not delegate API calls -- that's
        the proxmox role's job."""
        text = _read_build(self.TASKS)
        for marker in [
            "mthibaut.proxmox.proxmox_backup_job",
            "delegate_to: localhost",
            "proxmox_api_token_secret",
            "backup_jobs",
        ]:
            self.assertNotIn(marker, text, f"cluster-API call leaked into proxmox_host: {marker!r}")


class TestSiteYmlOrdering(unittest.TestCase):
    SITE = "site.yml"

    def test_proxmox_host_runs_before_proxmox(self):
        text = _read_build(self.SITE)
        host_idx = text.find("- role: proxmox_host")
        cluster_idx = text.find("- role: proxmox\n")
        self.assertGreater(host_idx, 0, "proxmox_host role missing from site.yml")
        self.assertGreater(cluster_idx, host_idx,
                           "proxmox role must follow proxmox_host in site.yml")

    def test_proxmox_host_activated_by_hypervisor_capability(self):
        text = _read_build(self.SITE)
        # Find the proxmox_host block
        block = text.split("- role: proxmox_host", 1)[1].split("- role: proxmox\n", 1)[0]
        self.assertIn("proxmox_host.enabled", block)
        self.assertIn("'hypervisor' in (_required_providers", block)


class TestCapabilityDispatch(unittest.TestCase):
    def test_hypervisor_maps_to_proxmox_host(self):
        # The canonical capabilities dict lives in roles/common/defaults;
        # group_vars/all/main.yml is comment-only documentation.
        text = _read_build("roles/common/defaults/main.yml")
        self.assertIn("hypervisor: {provider: proxmox_host}", text)
        self.assertNotIn("hypervisor: {provider: proxmox}\n", text)


class TestGenerationContracts(unittest.TestCase):
    def test_proxmox_host_files_registered(self):
        text = _read(GENERATION_CONTRACTS)
        self.assertIn("roles/proxmox_host/defaults/main.yml:", text)
        self.assertIn("roles/proxmox_host/handlers/main.yml:", text)
        self.assertIn("roles/proxmox_host/tasks/main.yml:", text)

    def test_old_proxmox_handlers_unregistered(self):
        """proxmox role no longer has handlers; the contract entry
        must be gone too."""
        text = _read(GENERATION_CONTRACTS)
        self.assertNotIn("roles/proxmox/handlers/main.yml:", text)


if __name__ == "__main__":
    unittest.main()
