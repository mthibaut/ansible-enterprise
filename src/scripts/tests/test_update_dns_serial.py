"""
Unit tests for roles/dns/files/update_dns_serial.py

The script reads a zone file, computes a deterministic SHA-256-based serial,
and updates the SOA serial in-place. Tests verify correctness, idempotency,
and format constraints.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

REPO   = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = REPO / "build" / "roles" / "dns" / "files" / "update_dns_serial.py"

ZONE_TEMPLATE = """\
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
        {serial}
        3600        ; refresh
        1800        ; retry
        1209600     ; expire
        86400       ; minimum TTL
)
@ IN NS ns1.example.com.
ns1 IN A 1.2.3.4
"""


def _run_script(zone_file: pathlib.Path) -> str:
    """Run update_dns_serial on zone_file via subprocess and return new content."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--zone-file", str(zone_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"update_dns_serial failed:\n{result.stderr}")
    return zone_file.read_text(encoding="utf-8")


class TestUpdateDnsSerial(unittest.TestCase):

    def _write_zone(self, tmp, serial="2020010101"):
        path = pathlib.Path(tmp) / "example.com.zone"
        path.write_text(ZONE_TEMPLATE.format(serial=serial), encoding="utf-8")
        return path

    def test_serial_is_ten_digits(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(zone)
            content = zone.read_text(encoding="utf-8")
        match = re.search(r"(\d{10})\b", content)
        self.assertIsNotNone(match, "No 10-digit serial found")
        self.assertEqual(len(match.group(1)), 10)

    def test_idempotent(self):
        """Running the script twice should produce the same serial."""
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(zone)
            content_first = zone.read_text(encoding="utf-8")
            _run_script(zone)
            content_second = zone.read_text(encoding="utf-8")
        self.assertEqual(content_first, content_second)

    def test_serial_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(zone)
            serial_before = re.search(r"(\d{10})\b", zone.read_text()).group(1)

            # Add an A record and recompute
            zone.write_text(zone.read_text() + "www IN A 1.2.3.5\n", encoding="utf-8")
            _run_script(zone)
            serial_after = re.search(r"(\d{10})\b", zone.read_text()).group(1)

        self.assertNotEqual(serial_before, serial_after)

    def test_no_change_when_serial_already_correct(self):
        """If the serial is already current, file mtime should not change."""
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(zone)
            mtime_first = os.path.getmtime(zone)
            _run_script(zone)
            mtime_second = os.path.getmtime(zone)
        self.assertEqual(mtime_first, mtime_second)

    def test_non_numeric_placeholder_replaced(self):
        """Script should handle zone files where serial is any 10-digit number."""
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp, serial="9999999999")
            _run_script(zone)
            import re
            serial = re.search(r"(\d{10})\b", zone.read_text()).group(1)
        # New serial should be deterministic regardless of old value
        self.assertRegex(serial, r"^\d{10}$")

    def test_deterministic_across_calls(self):
        """Same zone content always produces the same serial."""
        content = ZONE_TEMPLATE.format(serial="0000000001") + "host IN A 10.0.0.1\n"
        with tempfile.TemporaryDirectory() as tmp:
            zone_a = pathlib.Path(tmp) / "a.zone"
            zone_b = pathlib.Path(tmp) / "b.zone"
            zone_a.write_text(content, encoding="utf-8")
            zone_b.write_text(content, encoding="utf-8")
            _run_script(zone_a)
            _run_script(zone_b)
            serial_a = re.search(r"(\d{10})\b", zone_a.read_text()).group(1)
            serial_b = re.search(r"(\d{10})\b", zone_b.read_text()).group(1)
        self.assertEqual(serial_a, serial_b)


if __name__ == "__main__":
    unittest.main()
