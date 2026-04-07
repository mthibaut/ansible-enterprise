"""
Unit tests for roles/dns/files/dns-bump-serial.

The script bumps SOA serials using the YYYYMMDDNN convention, where YYYYMMDD
is today's date and NN increments for multiple same-day updates.
"""
import datetime
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

REPO   = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = REPO / "build" / "roles" / "dns" / "files" / "dns-bump-serial"

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


def _run_script(zone_dir, *zone_names, allow_direct_edit=True, check=True, env=None):
    """Run dns-bump-serial and return stdout."""
    cmd = [sys.executable, str(SCRIPT), "--zone-dir", str(zone_dir)]
    if allow_direct_edit:
        cmd.append("--allow-direct-edit")
    cmd.extend(zone_names)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"dns-bump-serial failed:\n{result.stderr}")
    return result


class TestDnsBumpSerial(unittest.TestCase):

    def _write_zone(self, tmp, name="example.com", serial="2020010101"):
        path = pathlib.Path(tmp) / (name + ".zone")
        path.write_text(ZONE_TEMPLATE.format(serial=serial), encoding="utf-8")
        return path

    def test_serial_is_ten_digits(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_zone(tmp)
            result = _run_script(tmp, "example.com")
            self.assertEqual(result.returncode, 0)
            content = (pathlib.Path(tmp) / "example.com.zone").read_text()
        match = re.search(r"(\d{10})\b", content)
        self.assertIsNotNone(match, "No 10-digit serial found")
        self.assertEqual(len(match.group(1)), 10)

    def test_idempotent(self):
        """Running twice on the same day should increment the NN suffix."""
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(tmp, "example.com")
            serial_first = re.search(r"(\d{10})\b", zone.read_text()).group(1)
            _run_script(tmp, "example.com")
            serial_second = re.search(r"(\d{10})\b", zone.read_text()).group(1)
        self.assertEqual(int(serial_second), int(serial_first) + 1)

    def test_serial_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(tmp, "example.com")
            serial_before = re.search(r"(\d{10})\b", zone.read_text()).group(1)

            # Add an A record and recompute
            zone.write_text(zone.read_text() + "www IN A 1.2.3.5\n", encoding="utf-8")
            _run_script(tmp, "example.com")
            serial_after = re.search(r"(\d{10})\b", zone.read_text()).group(1)

        self.assertEqual(int(serial_after), int(serial_before) + 1)

    def test_old_serial_jumps_to_today_first_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            _run_script(tmp, "example.com")
            serial = re.search(r"(\d{10})\b", zone.read_text()).group(1)
        self.assertEqual(serial, datetime.date.today().strftime("%Y%m%d") + "01")

    def test_same_day_serial_increments_suffix(self):
        today_serial = datetime.date.today().strftime("%Y%m%d") + "07"
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp, serial=today_serial)
            _run_script(tmp, "example.com")
            serial = re.search(r"(\d{10})\b", zone.read_text()).group(1)
        self.assertEqual(serial, datetime.date.today().strftime("%Y%m%d") + "08")

    def test_out_of_range_serial_fails(self):
        """Out-of-range serials should fail clearly for manual repair."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_zone(tmp, serial="9999999999")
            result = _run_script(tmp, "example.com", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds the DNS SOA serial range", result.stderr)

    def test_same_inputs_same_starting_serial_produce_same_next_serial(self):
        content = ZONE_TEMPLATE.format(serial="0000000001") + "host IN A 10.0.0.1\n"
        with tempfile.TemporaryDirectory() as tmp:
            zone_a = pathlib.Path(tmp) / "a.zone"
            zone_b = pathlib.Path(tmp) / "b.zone"
            zone_a.write_text(content, encoding="utf-8")
            zone_b.write_text(content, encoding="utf-8")
            _run_script(tmp, "a")
            _run_script(tmp, "b")
            serial_a = re.search(r"(\d{10})\b", zone_a.read_text()).group(1)
            serial_b = re.search(r"(\d{10})\b", zone_b.read_text()).group(1)
        self.assertEqual(serial_a, serial_b)

    def test_all_zones_when_no_args(self):
        """With no zone names, all .zone files should be bumped."""
        with tempfile.TemporaryDirectory() as tmp:
            zone_a = self._write_zone(tmp, name="a.example")
            zone_b = self._write_zone(tmp, name="b.example")
            output = _run_script(tmp).stdout
            self.assertIn("a.example", output)
            self.assertIn("b.example", output)

    def test_changed_output(self):
        """Script should print CHANGED when serial is updated."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_zone(tmp)
            output = _run_script(tmp, "example.com").stdout
        self.assertIn("CHANGED", output)

    def test_second_run_still_reports_changed(self):
        """Date-based serials increment on repeated same-day runs."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_zone(tmp)
            _run_script(tmp, "example.com")
            output = _run_script(tmp, "example.com").stdout
        self.assertIn("CHANGED", output)

    def test_requires_explicit_direct_edit_opt_in_without_rndc(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_zone(tmp)
            env = dict(os.environ)
            env["PATH"] = ""
            result = _run_script(
                tmp, "example.com", allow_direct_edit=False, check=False, env=env
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rndc is required", result.stderr)

    def test_allow_direct_edit_when_rndc_reports_zone_not_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            zone = self._write_zone(tmp)
            bindir = pathlib.Path(tmp) / "bin"
            bindir.mkdir()
            fake_rndc = bindir / "rndc"
            fake_rndc.write_text(
                "#!/bin/sh\n"
                "echo \"rndc: '$1' failed: not found\" 1>&2\n"
                "echo \"no matching zone '$2' in any view\" 1>&2\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_rndc.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = str(bindir)
            result = _run_script(tmp, "example.com", env=env)
            serial = re.search(r"(\d{10})\b", zone.read_text()).group(1)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(serial, datetime.date.today().strftime("%Y%m%d") + "01")


if __name__ == "__main__":
    unittest.main()
