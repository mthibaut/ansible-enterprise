from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.scripts import wireguard_topology_render as wtr


TOPOLOGY = {
    "hosts": {
        "be-fw": {"endpoint": "be.example.com"},
        "nl": {"endpoint": "nl.example.com"},
    },
    "clients": {
        "laptop": {"octet": 50},
    },
    "networks": {
        "core": {
            "type": "mesh",
            "port": 51820,
            "subnet": "172.16.0.0/29",
            "members": ["be-fw", "nl"],
            "member_routes": {
                "be-fw": ["192.168.0.0/16"],
            },
        },
        "home": {
            "type": "hub",
            "port": 51821,
            "subnet": "172.16.1.0/24",
            "hub": "be-fw",
            "extra_routes": ["192.168.0.0/16"],
            "clients": ["laptop"],
        },
    },
}


class TestWireguardTopologyRender(unittest.TestCase):
    def test_build_host_doc_for_hub_client(self):
        state = wtr.State(
            priv={
                ("be-fw", "home"): "priv-fw",
                ("laptop", "home"): "priv-laptop",
            },
            pub={
                ("be-fw", "home"): "pub-fw",
                ("laptop", "home"): "pub-laptop",
            },
            psk={
                ("home", frozenset({"be-fw", "laptop"})): "psk-home",
            },
        )
        doc = wtr.build_host_doc("laptop", TOPOLOGY, state)
        instance = doc["wireguard_instances"][0]
        self.assertEqual(instance["name"], "wg-home")
        self.assertEqual(instance["address"], ["172.16.1.50/24"])
        self.assertEqual(instance["private_key"], "{{ vault_wireguard_home_private_key }}")
        self.assertEqual(instance["peers"][0]["endpoint"], "be.example.com:51821")
        self.assertEqual(instance["peers"][0]["allowed_ips"], ["172.16.1.1/32", "192.168.0.0/16"])

    def test_render_conf_for_mesh_member_includes_peer_routes(self):
        state = wtr.State(
            priv={
                ("be-fw", "core"): "priv-fw",
                ("nl", "core"): "priv-nl",
            },
            pub={
                ("be-fw", "core"): "pub-fw",
                ("nl", "core"): "pub-nl",
            },
            psk={
                ("core", frozenset({"be-fw", "nl"})): "psk-core",
            },
        )
        text = wtr.render_wg_conf("nl", "core", TOPOLOGY["networks"]["core"], TOPOLOGY, state)
        self.assertIn("Address = 172.16.0.2/29", text)
        self.assertIn("ListenPort = 51820", text)
        self.assertIn("AllowedIPs = 172.16.0.1/29, 192.168.0.0/16", text)
        self.assertIn("Endpoint = be.example.com:51820", text)
        self.assertIn("PersistentKeepalive = 25", text)

    def test_main_writes_host_vars_vault_and_conf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topology_path = root / "topology.yml"
            topology_path.write_text(yaml.safe_dump(TOPOLOGY, sort_keys=False), encoding="utf-8")

            original_gen_keypair = wtr.gen_keypair
            original_gen_psk = wtr.gen_psk
            keypairs = iter(
                [
                    ("priv-be-fw-core", "pub-be-fw-core"),
                    ("priv-nl-core", "pub-nl-core"),
                    ("priv-be-fw-home", "pub-be-fw-home"),
                    ("priv-laptop-home", "pub-laptop-home"),
                ]
            )
            psks = iter(["psk-core", "psk-home"])

            wtr.gen_keypair = lambda: next(keypairs)
            wtr.gen_psk = lambda: next(psks)
            try:
                rc = wtr.main(["-i", str(root), "-t", str(topology_path)])
            finally:
                wtr.gen_keypair = original_gen_keypair
                wtr.gen_psk = original_gen_psk

            self.assertEqual(rc, 0)
            host_doc = yaml.safe_load((root / "host_vars" / "laptop" / "wireguard.yml").read_text())
            self.assertEqual(host_doc["wireguard_public_keys"]["home"], "pub-laptop-home")
            conf = (root / "wg-conf" / "laptop" / "wg-home.conf").read_text()
            self.assertIn("PrivateKey = priv-laptop-home", conf)
            self.assertIn("Endpoint = be.example.com:51821", conf)
            vault_doc = yaml.safe_load((root / "host_vars" / "be-fw" / "wireguard_vault_home.yml").read_text())
            self.assertEqual(vault_doc["vault_wireguard_home_private_key"], "priv-be-fw-home")
            self.assertEqual(vault_doc["vault_wg_psk_home_laptop"], "psk-home")
