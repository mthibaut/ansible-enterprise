import os
import pathlib
import io
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "scripts"))

import proxmox_infra_render as rpi
import proxmox_inventory_scaffold as spi


class TestRenderProxmoxInfra(unittest.TestCase):

    def test_build_lxc_infra_config(self):
        data = rpi.build_infra_config(
            provider="proxmox",
            instance_type="lxc",
            instance_id=200,
            artifact="almalinux-9-default_20240911_amd64.tar.xz",
            ip_cidr="192.0.2.11/24",
            gateway="192.0.2.1",
            node="pve01",
            cores=2,
            memory=1024,
        )
        self.assertEqual(data["provider"], "proxmox")
        self.assertEqual(data["type"], "lxc")
        self.assertEqual(data["id"], 200)
        self.assertEqual(data["proxmox"]["ostemplate"], "local:vztmpl/almalinux-9-default_20240911_amd64.tar.xz")
        self.assertEqual(data["proxmox"]["net"]["ip"], "192.0.2.11/24")
        self.assertEqual(data["proxmox"]["net"]["gw"], "192.0.2.1")
        self.assertEqual(data["proxmox"]["node"], "pve01")

    def test_build_vm_infra_config(self):
        data = rpi.build_infra_config(
            provider="proxmox",
            instance_type="vm",
            instance_id=110,
            artifact="ubuntu-noble-ci",
            ip_cidr="192.0.2.90/24",
            gateway="192.0.2.1",
        )
        self.assertEqual(data["type"], "vm")
        self.assertEqual(data["proxmox"]["template_name"], "ubuntu-noble-ci")
        self.assertEqual(data["proxmox"]["net"]["gw"], "192.0.2.1")

    def test_build_lxc_infra_config_normalizes_bare_artifact_storage(self):
        data = rpi.build_infra_config(
            provider="proxmox",
            instance_type="lxc",
            instance_id=200,
            artifact="almalinux-10-default_20250930_amd64.tar.xz",
            artifact_storage="synology-pve",
            ip_cidr="192.0.2.10/24",
        )
        self.assertEqual(
            data["proxmox"]["ostemplate"],
            "synology-pve:vztmpl/almalinux-10-default_20250930_amd64.tar.xz",
        )

    def test_build_infra_config_rejects_unsupported_provider(self):
        with self.assertRaisesRegex(ValueError, "unsupported provider"):
            rpi.build_infra_config(
                provider="aws",
                instance_type="vm",
                instance_id=110,
                artifact="ubuntu-noble-ci",
                ip_cidr="192.0.2.90/24",
            )

    def test_render_help_lists_environment_variables(self):
        buf = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(buf):
                rpi.parse_args(["--help"])
        text = buf.getvalue()
        self.assertIn("Environment variable defaults:", text)
        self.assertIn("PROXMOX_CORES", text)
        self.assertIn("CLI flags override environment variables.", text)
        self.assertIn("vCPU count override.", text)
        self.assertIn("Boolean variables accept: 1/0, true/false, yes/no, on/off", text)

    def test_parse_args_uses_environment_defaults(self):
        with mock.patch.dict(
            os.environ,
            {
                "PROXMOX_TYPE": "lxc",
                "PROXMOX_ID": "200",
                "PROXMOX_ARTIFACT": "almalinux-9-default_20240911_amd64.tar.xz",
                "PROXMOX_IP": "192.0.2.11/24",
                "PROXMOX_NODE": "pve01",
                "PROXMOX_CORES": "2",
                "PROXMOX_ONBOOT": "true",
            },
            clear=False,
        ):
            args = rpi.parse_args([])
        self.assertEqual(args.provider, "proxmox")
        self.assertEqual(args.instance_type, "lxc")
        self.assertEqual(args.instance_id, 200)
        self.assertEqual(args.node, "pve01")
        self.assertEqual(args.cores, 2)
        self.assertTrue(args.onboot)

    def test_render_cli_overrides_environment_defaults(self):
        with mock.patch.dict(
            os.environ,
            {
                "PROXMOX_TYPE": "lxc",
                "PROXMOX_ID": "200",
                "PROXMOX_ARTIFACT": "old-template.tar.xz",
                "PROXMOX_IP": "192.0.2.11/24",
            },
            clear=False,
        ):
            args = rpi.parse_args(["--artifact", "new-template.tar.xz", "--id", "201"])
        self.assertEqual(args.artifact, "new-template.tar.xz")
        self.assertEqual(args.instance_id, 201)


class TestScaffoldProxmoxInventory(unittest.TestCase):

    def test_parse_rows(self):
        rows = spi.parse_rows(
            "almalinux-10 almalinux-10-default_20250930_amd64.tar.xz\n"
            "\n"
            "# comment\n"
            "alpine-3-22 alpine-3.22-default_20250617_amd64.tar.xz\n"
        )
        self.assertEqual(
            rows,
            [
                ("almalinux-10", "almalinux-10-default_20250930_amd64.tar.xz"),
                ("alpine-3-22", "alpine-3.22-default_20250617_amd64.tar.xz"),
            ],
        )

    def test_increment_ip(self):
        self.assertEqual(spi.increment_ip("192.0.2.10/24", 0), "192.0.2.10/24")
        self.assertEqual(spi.increment_ip("192.0.2.10/24", 2), "192.0.2.12/24")

    def test_write_inventory(self):
        rows = [
            ("almalinux-10", "almalinux-10-default_20250930_amd64.tar.xz"),
            ("almalinux-9", "almalinux-9-default_20240911_amd64.tar.xz"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            spi.write_inventory(
                rows=rows,
                out_dir=out_dir,
                provider="proxmox",
                instance_type="lxc",
                id_start=200,
                ip_start_cidr="192.0.2.10/24",
                gateway="192.0.2.1",
                bridge="vmbr0",
                state="present",
                rebuild_on="never",
                ansible_user="root",
                ansible_group="all",
                ansible_port=None,
                ansible_connection=None,
                ansible_become=None,
                ansible_become_method=None,
                node="pve01",
                storage=None,
                artifact_storage="local:vztmpl",
                cores=None,
                memory=None,
                disk=None,
                nameserver=None,
                searchdomain=None,
                onboot=None,
                started=None,
                unprivileged=None,
                force=False,
            )
            hosts_ini = (out_dir / "hosts.ini").read_text(encoding="utf-8")
            self.assertIn("[all]", hosts_ini)
            self.assertIn("almalinux-10 ansible_host=192.0.2.10 ansible_user=root", hosts_ini)
            host_var = (out_dir / "host_vars" / "almalinux-9" / "infra.yml").read_text(encoding="utf-8")
            self.assertIn("provider: proxmox", host_var)
            self.assertIn("type: lxc", host_var)
            self.assertIn("id: 201", host_var)
            self.assertIn("ip: 192.0.2.11/24", host_var)
            self.assertIn("ostemplate: local:vztmpl/almalinux-9-default_20240911_amd64.tar.xz", host_var)

    def test_write_inventory_for_vm_uses_template_name(self):
        rows = [
            ("ubuntu-noble", "ubuntu-noble-ci"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp)
            spi.write_inventory(
                rows=rows,
                out_dir=out_dir,
                provider="proxmox",
                instance_type="vm",
                id_start=110,
                ip_start_cidr="192.0.2.90/24",
                gateway="192.0.2.1",
                bridge="vmbr0",
                state="present",
                rebuild_on="config_change",
                ansible_user="root",
                ansible_group="all",
                ansible_port=None,
                ansible_connection=None,
                ansible_become=None,
                ansible_become_method=None,
                node="pve01",
                storage=None,
                artifact_storage="local:vztmpl",
                cores=4,
                memory=4096,
                disk=None,
                nameserver=None,
                searchdomain=None,
                onboot=None,
                started=None,
                unprivileged=None,
                force=False,
            )
            host_var = (out_dir / "host_vars" / "ubuntu-noble" / "infra.yml").read_text(encoding="utf-8")
            self.assertIn("type: vm", host_var)
            self.assertIn("id: 110", host_var)
            self.assertIn("rebuild_on: config_change", host_var)
            self.assertIn("template_name: ubuntu-noble-ci", host_var)
            self.assertIn("ip: 192.0.2.90/24", host_var)

    def test_scaffold_parse_args_uses_environment_defaults(self):
        with mock.patch.dict(
            os.environ,
            {
                "PROXMOX_PROVIDER": "proxmox",
                "PROXMOX_TYPE": "vm",
                "PROXMOX_ID_START": "110",
                "PROXMOX_IP_START": "192.0.2.90/24",
                "PROXMOX_NODE": "pve01",
                "PROXMOX_MEMORY": "4096",
            },
            clear=False,
        ):
            args = spi.parse_args([])
        self.assertEqual(args.provider, "proxmox")
        self.assertEqual(args.instance_type, "vm")
        self.assertEqual(args.id_start, 110)
        self.assertEqual(args.ip_start, "192.0.2.90/24")
        self.assertEqual(args.node, "pve01")
        self.assertEqual(args.memory, 4096)

    def test_scaffold_cli_overrides_environment_defaults(self):
        with mock.patch.dict(
            os.environ,
            {
                "PROXMOX_TYPE": "vm",
                "PROXMOX_ID_START": "110",
                "PROXMOX_IP_START": "192.0.2.90/24",
            },
            clear=False,
        ):
            args = spi.parse_args(["--type", "lxc", "--id-start", "200"])
        self.assertEqual(args.provider, "proxmox")
        self.assertEqual(args.instance_type, "lxc")
        self.assertEqual(args.id_start, 200)

    def test_scaffold_main_rejects_unsupported_provider(self):
        with self.assertRaisesRegex(ValueError, "unsupported provider"):
            spi.main(["--provider", "aws", "--type", "vm", "--id-start", "110", "--ip-start", "192.0.2.90/24"])

    def test_scaffold_help_lists_environment_variables(self):
        buf = io.StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(buf):
                spi.parse_args(["--help"])
        text = buf.getvalue()
        self.assertIn("Environment variable defaults:", text)
        self.assertIn("PROXMOX_ID_START", text)
        self.assertIn("PROXMOX_IP_START", text)
        self.assertIn("Starting guest IP/CIDR for scaffolded hosts", text)


if __name__ == "__main__":
    unittest.main()
