"""
Unit tests for roles/geoip/files/geoip_ingest.py

Tests use synthetic MaxMind-format CSV data to avoid any real download.
The GeoLite2-Country archive structure:
  GeoLite2-Country-Blocks-IPv4.csv  — network, geoname_id, registered_country_geoname_id
  GeoLite2-Country-Blocks-IPv6.csv  — same schema
  GeoLite2-Country-Locations-en.csv — geoname_id, country_iso_code, ...
"""
import importlib.util
import io
import pathlib
import sys
import tempfile
import textwrap
import unittest
import zipfile

# ---------------------------------------------------------------------------
# Load geoip_ingest from build/ without installing it as a package
# ---------------------------------------------------------------------------
REPO = pathlib.Path(__file__).resolve().parents[3]
INGEST_PATH = REPO / "build" / "roles" / "geoip" / "files" / "geoip_ingest.py"


def _load_ingest():
    spec = importlib.util.spec_from_file_location("geoip_ingest", INGEST_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Synthetic CSV helpers
# ---------------------------------------------------------------------------
LOCATIONS_HEADER = "geoname_id,locale_code,continent_code,continent_name,country_iso_code,country_name,is_in_european_union\n"
BLOCKS_HEADER    = "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,is_anonymous_proxy,is_satellite_provider\n"

def _make_locations(*rows):
    """rows: list of (geoname_id, country_iso_code) tuples"""
    lines = LOCATIONS_HEADER
    for gid, iso in rows:
        lines += f"{gid},en,EU,Europe,{iso},{iso} Country,0\n"
    return lines

def _make_blocks(*rows):
    """rows: list of (network, geoname_id) tuples"""
    lines = BLOCKS_HEADER
    for net, gid in rows:
        lines += f"{net},{gid},{gid},,0,0\n"
    return lines

def _make_archive(tmp_dir, locations_csv, ipv4_csv, ipv6_csv=None):
    """Write a synthetic GeoLite2-Country-CSV zip into tmp_dir and return its path."""
    archive_path = pathlib.Path(tmp_dir) / "GeoLite2-Country-CSV.zip"
    prefix = "GeoLite2-Country-CSV_20240101/"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr(prefix + "GeoLite2-Country-Locations-en.csv", locations_csv)
        zf.writestr(prefix + "GeoLite2-Country-Blocks-IPv4.csv", ipv4_csv)
        zf.writestr(prefix + "GeoLite2-Country-Blocks-IPv6.csv",
                    ipv6_csv or BLOCKS_HEADER)
    return archive_path


class TestLoadGeonameMap(unittest.TestCase):
    def setUp(self):
        self.mod = _load_ingest()

    def test_basic_map(self):
        locations = _make_locations(("2802361", "BE"), ("2635167", "GB"))
        with tempfile.TemporaryDirectory() as tmp:
            archive = _make_archive(tmp, locations, BLOCKS_HEADER)
            import zipfile as zf
            extract = pathlib.Path(tmp) / "extracted"
            extract.mkdir()
            with zf.ZipFile(archive) as z:
                z.extractall(extract)
            result = self.mod.load_geoname_map(extract)
        self.assertEqual(result["2802361"], "BE")
        self.assertEqual(result["2635167"], "GB")

    def test_empty_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = _make_archive(tmp, LOCATIONS_HEADER, BLOCKS_HEADER)
            import zipfile as zf
            extract = pathlib.Path(tmp) / "extracted"
            extract.mkdir()
            with zf.ZipFile(archive) as z:
                z.extractall(extract)
            result = self.mod.load_geoname_map(extract)
        self.assertEqual(result, {})


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.mod = _load_ingest()

    def _collect(self, blocks_csv, countries, geoname_map):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv",
                                         delete=False, encoding="utf-8") as f:
            f.write(blocks_csv)
            path = pathlib.Path(f.name)
        try:
            return self.mod.collect([path], countries, geoname_map)
        finally:
            path.unlink()

    def test_matching_country(self):
        geoname_map = {"2802361": "BE"}
        blocks = _make_blocks(("1.2.3.0/24", "2802361"), ("5.6.7.0/24", "2802361"))
        result = self._collect(blocks, {"BE"}, geoname_map)
        self.assertIn("1.2.3.0/24", result)
        self.assertIn("5.6.7.0/24", result)

    def test_non_matching_country(self):
        geoname_map = {"2802361": "BE", "2635167": "GB"}
        blocks = _make_blocks(("1.2.3.0/24", "2802361"), ("5.6.7.0/24", "2635167"))
        result = self._collect(blocks, {"BE"}, geoname_map)
        self.assertIn("1.2.3.0/24", result)
        self.assertNotIn("5.6.7.0/24", result)

    def test_registered_country_fallback(self):
        """Blocks with no geoname_id should resolve via registered_country_geoname_id."""
        geoname_map = {"2802361": "BE"}
        # Write a block with empty geoname_id but a registered_country_geoname_id
        blocks = BLOCKS_HEADER + "9.9.9.0/24,,2802361,,0,0\n"
        result = self._collect(blocks, {"BE"}, geoname_map)
        self.assertIn("9.9.9.0/24", result)

    def test_empty_geoname_map_yields_nothing(self):
        """The old bug: country_iso_code column not in blocks → empty results."""
        blocks = _make_blocks(("1.2.3.0/24", "2802361"))
        result = self._collect(blocks, {"BE"}, {})
        self.assertEqual(result, [])

    def test_results_sorted_and_deduplicated(self):
        geoname_map = {"1": "BE"}
        blocks = BLOCKS_HEADER + "10.0.0.0/8,1,1,,0,0\n10.0.0.0/8,1,1,,0,0\n1.0.0.0/8,1,1,,0,0\n"
        result = self._collect(blocks, {"BE"}, geoname_map)
        self.assertEqual(result, sorted(set(result)))
        self.assertEqual(len(result), len(set(result)))


class TestMain(unittest.TestCase):
    """End-to-end test of main(): synthetic archive → .nft files."""

    def setUp(self):
        self.mod = _load_ingest()

    def _run_main(self, countries_list, set_prefix="geoip_allowed",
                   ipv4_rows=None, ipv6_rows=None, geoname_rows=None):
        ipv4_rows = ipv4_rows or []
        ipv6_rows = ipv6_rows or []
        geoname_rows = geoname_rows or []

        locations = _make_locations(*geoname_rows)
        ipv4_csv  = _make_blocks(*ipv4_rows)
        ipv6_csv  = _make_blocks(*ipv6_rows)

        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            dl_dir   = tmp / "download"
            sets_dir = tmp / "sets"
            dl_dir.mkdir()
            sets_dir.mkdir()

            # Archive is written directly into dl_dir as the filename main() expects
            _make_archive(dl_dir, locations, ipv4_csv, ipv6_csv)

            countries_file = dl_dir / "countries.txt"
            countries_file.write_text("\n".join(countries_list) + "\n", encoding="utf-8")

            import unittest.mock as mock
            with mock.patch("urllib.request.urlretrieve"):
                sys.argv = [
                    "geoip_ingest.py",
                    "--license-key", "TESTKEY",
                    "--download-dir", str(dl_dir),
                    "--sets-dir", str(sets_dir),
                    "--countries-file", str(countries_file),
                    "--set-prefix", set_prefix,
                ]
                self.mod.main()

            ipv4_nft = (sets_dir / f"{set_prefix}_ipv4.nft").read_text(encoding="utf-8")
            ipv6_nft = (sets_dir / f"{set_prefix}_ipv6.nft").read_text(encoding="utf-8")
            return ipv4_nft, ipv6_nft

    def test_empty_countries_produces_empty_set(self):
        ipv4, ipv6 = self._run_main([])
        self.assertIn("geoip_allowed_ipv4 = { }", ipv4)
        self.assertIn("geoip_allowed_ipv6 = { }", ipv6)

    def test_matching_country_produces_cidrs(self):
        ipv4, _ = self._run_main(
            countries_list=["BE"],
            geoname_rows=[("2802361", "BE"), ("2635167", "GB")],
            ipv4_rows=[("1.2.3.0/24", "2802361"), ("5.6.0.0/16", "2635167")],
        )
        self.assertIn("1.2.3.0/24", ipv4)
        self.assertNotIn("5.6.0.0/16", ipv4)

    def test_set_prefix_applied(self):
        ipv4, ipv6 = self._run_main(
            countries_list=[],
            set_prefix="geoip_ssh",
        )
        self.assertIn("geoip_ssh_ipv4 =", ipv4)
        self.assertIn("geoip_ssh_ipv6 =", ipv6)

    def test_case_insensitive_country_codes(self):
        ipv4, _ = self._run_main(
            countries_list=["be"],  # lowercase
            geoname_rows=[("2802361", "BE")],
            ipv4_rows=[("1.2.3.0/24", "2802361")],
        )
        self.assertIn("1.2.3.0/24", ipv4)

    def test_ipv6_cidr_written_to_ipv6_file(self):
        _, ipv6 = self._run_main(
            countries_list=["BE"],
            geoname_rows=[("2802361", "BE")],
            ipv6_rows=[("2a02::/32", "2802361")],
        )
        self.assertIn("2a02::/32", ipv6)


if __name__ == "__main__":
    unittest.main()


class TestDownloadFlags(unittest.TestCase):
    """Tests for --download-only and --skip-download flags."""

    def setUp(self):
        self.mod = _load_ingest()

    def test_download_only_exits_without_generating_sets(self):
        """--download-only should download the archive and return without writing .nft files."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            dl_dir   = tmp / "download"
            sets_dir = tmp / "sets"
            dl_dir.mkdir(); sets_dir.mkdir()
            countries_file = dl_dir / "countries.txt"
            countries_file.write_text("BE\n")
            # Pre-place a valid archive so main() can open it
            _make_archive(dl_dir,
                          _make_locations(("2802361", "BE")),
                          _make_blocks(("1.2.3.0/24", "2802361")))
            import unittest.mock as mock
            with mock.patch("urllib.request.urlretrieve"):
                sys.argv = [
                    "geoip_ingest.py",
                    "--license-key", "TESTKEY",
                    "--download-dir", str(dl_dir),
                    "--sets-dir", str(sets_dir),
                    "--countries-file", str(countries_file),
                    "--download-only",
                ]
                self.mod.main()
            # No .nft files should have been written
            nft_files = list(sets_dir.glob("*.nft"))
            self.assertEqual(nft_files, [],
                             f"--download-only should not generate .nft files, found: {nft_files}")

    def test_skip_download_uses_existing_archive(self):
        """--skip-download should generate sets from the existing archive without downloading."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            dl_dir   = tmp / "download"
            sets_dir = tmp / "sets"
            dl_dir.mkdir(); sets_dir.mkdir()
            _make_archive(dl_dir,
                          _make_locations(("2802361", "BE")),
                          _make_blocks(("1.2.3.0/24", "2802361")))
            countries_file = dl_dir / "countries.txt"
            countries_file.write_text("BE\n")
            import unittest.mock as mock
            with mock.patch("urllib.request.urlretrieve") as mock_dl:
                sys.argv = [
                    "geoip_ingest.py",
                    "--license-key", "TESTKEY",
                    "--download-dir", str(dl_dir),
                    "--sets-dir", str(sets_dir),
                    "--countries-file", str(countries_file),
                    "--skip-download",
                ]
                self.mod.main()
                mock_dl.assert_not_called()
            ipv4 = (sets_dir / "geoip_allowed_ipv4.nft").read_text()
            self.assertIn("1.2.3.0/24", ipv4)

    def test_skip_download_missing_archive_raises(self):
        """--skip-download with no existing archive should raise an error."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            dl_dir   = tmp / "download"
            sets_dir = tmp / "sets"
            dl_dir.mkdir(); sets_dir.mkdir()
            countries_file = dl_dir / "countries.txt"
            countries_file.write_text("BE\n")
            sys.argv = [
                "geoip_ingest.py",
                "--license-key", "TESTKEY",
                "--download-dir", str(dl_dir),
                "--sets-dir", str(sets_dir),
                "--countries-file", str(countries_file),
                "--skip-download",
            ]
            with self.assertRaises((FileNotFoundError, Exception)):
                self.mod.main()

    def test_download_only_without_sets_or_countries_args(self):
        """--download-only should work without --sets-dir or --countries-file."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            dl_dir = tmp / "download"
            dl_dir.mkdir()
            import unittest.mock as mock
            with mock.patch("urllib.request.urlretrieve"):
                sys.argv = [
                    "geoip_ingest.py",
                    "--license-key", "TESTKEY",
                    "--download-dir", str(dl_dir),
                    "--download-only",
                ]
                self.mod.main()
            # Should complete without error; no .nft files anywhere
            nft_files = list(dl_dir.glob("*.nft"))
            self.assertEqual(nft_files, [])