"""
Unit tests for roles/dns/files/sync_dns_records.py

Tests record_exists() and remove_record() directly, plus end-to-end CLI
invocation via subprocess to cover argument parsing.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO   = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = REPO / "build" / "roles" / "dns" / "files" / "sync_dns_records.py"

# Minimal zone file matching what zone.db.j2 generates
ZONE_BASE = """\
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
        2026010101  ; serial
        3600        ; refresh
        1800        ; retry
        1209600     ; expire
        86400       ; minimum TTL
)
@ IN NS ns1.example.com.
ns1             IN  A   1.2.3.4
"""

sys.path.insert(0, str(SCRIPT.parent))
from sync_dns_records import record_exists, remove_record


def _write_zone(tmp, extra=""):
    path = pathlib.Path(tmp) / "example.com.zone"
    path.write_text(ZONE_BASE + extra, encoding="utf-8")
    return path


def _run_cli(zone_file, records, absent=False, ttl=None):
    """Run the script via subprocess; returns (returncode, stdout, stderr)."""
    args = [sys.executable, str(SCRIPT), "--zone-file", str(zone_file)]
    for label, rtype, value in records:
        args += ["--record", label, rtype, value]
    if ttl is not None:
        args += ["--ttl", str(ttl)]
    if absent:
        args += ["--absent"]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestRecordExists(unittest.TestCase):

    def test_a_record_found(self):
        self.assertTrue(record_exists("@       IN  A   1.2.3.4\n", "@", "A", "1.2.3.4"))

    def test_a_record_not_found(self):
        self.assertFalse(record_exists("@       IN  A   1.2.3.4\n", "@", "A", "9.9.9.9"))

    def test_subdomain_found(self):
        self.assertTrue(record_exists("app     IN  A   1.2.3.4\n", "app", "A", "1.2.3.4"))

    def test_mx_record_found(self):
        self.assertTrue(record_exists("@   IN  MX  10 mail.example.com.\n",
                                      "@", "MX", "10 mail.example.com."))

    def test_txt_record_found(self):
        self.assertTrue(record_exists('@   IN  TXT "v=spf1 mx ~all"\n',
                                      "@", "TXT", '"v=spf1 mx ~all"'))

    def test_wrong_type_not_found(self):
        self.assertFalse(record_exists("@   IN  A   1.2.3.4\n", "@", "MX", "1.2.3.4"))

    def test_flexible_whitespace(self):
        self.assertTrue(record_exists("@\tIN\tA\t1.2.3.4\n", "@", "A", "1.2.3.4"))

    def test_with_ttl(self):
        self.assertTrue(record_exists("app 86400 IN A 1.2.3.4\n", "app", "A", "1.2.3.4"))

    def test_case_insensitive(self):
        self.assertTrue(record_exists("app IN a 1.2.3.4\n", "app", "A", "1.2.3.4"))

    def test_partial_label_not_matched(self):
        self.assertFalse(record_exists("appserver IN A 1.2.3.4\n", "app", "A", "1.2.3.4"))

    def test_partial_address_not_matched(self):
        self.assertFalse(record_exists("@ IN A 1.2.3.40\n", "@", "A", "1.2.3.4"))


class TestRemoveRecord(unittest.TestCase):

    def test_removes_existing(self):
        text = "@ IN A 1.2.3.4\napp IN A 2.3.4.5\n"
        result = remove_record(text, "@", "A", "1.2.3.4")
        self.assertNotIn("1.2.3.4", result)
        self.assertIn("app", result)

    def test_noop_when_absent(self):
        text = "app IN A 1.2.3.4\n"
        result = remove_record(text, "old", "A", "1.2.3.4")
        self.assertEqual(text, result)


class TestCLI(unittest.TestCase):

    def test_adds_missing_a_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp)
            rc, out, err = _run_cli(zone, [("app", "A", "5.6.7.8")])
        self.assertEqual(rc, 0)
        self.assertIn("added", out)

    def test_silent_when_record_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp, extra="app IN A 5.6.7.8\n")
            rc, out, err = _run_cli(zone, [("app", "A", "5.6.7.8")])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_idempotent_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp)
            _run_cli(zone, [("app", "A", "5.6.7.8")])
            rc, out, _ = _run_cli(zone, [("app", "A", "5.6.7.8")])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_absent_removes_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp, extra="old IN A 1.2.3.4\n")
            rc, out, _ = _run_cli(zone, [("old", "A", "1.2.3.4")], absent=True)
            content = zone.read_text()
        self.assertEqual(rc, 0)
        self.assertIn("removed", out)
        self.assertNotIn("1.2.3.4", content.split("1.2.3.4\n", 1)[-1])

    def test_absent_noop_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp)
            rc, out, _ = _run_cli(zone, [("old", "A", "1.2.3.4")], absent=True)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_adds_mx_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp)
            rc, out, _ = _run_cli(zone, [("@", "MX", "10 mail.example.com.")])
            content = zone.read_text()
        self.assertEqual(rc, 0)
        self.assertIn("MX", content)

    def test_ttl_written_in_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp)
            _run_cli(zone, [("app", "A", "5.6.7.8")], ttl=300)
            content = zone.read_text()
        self.assertIn("300", content)

    def test_missing_zone_file_exits_nonzero(self):
        rc, _, _ = _run_cli(pathlib.Path("/nonexistent/zone.zone"), [])
        self.assertNotEqual(rc, 0)

    def test_hand_added_records_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp, extra="manual IN A 9.9.9.9\n")
            _run_cli(zone, [("app", "A", "5.6.7.8")])
            content = zone.read_text()
        self.assertIn("manual", content)
        self.assertIn("9.9.9.9", content)

    def test_no_records_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = _write_zone(tmp)
            rc, out, _ = _run_cli(zone, [])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
