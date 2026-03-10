#!/usr/bin/env python3
import argparse
import csv
import pathlib
import shutil
import tempfile
import urllib.request
import zipfile

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--license-key", required=True)
    ap.add_argument("--download-dir", required=True)
    ap.add_argument("--sets-dir", required=True)
    ap.add_argument("--countries-file", required=True)
    return ap.parse_args()

def collect(paths, countries):
    cidrs = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("country_iso_code", "").upper() in countries:
                    cidrs.append(row["network"])
    return sorted(set(cidrs))

def main():
    args = parse_args()
    download_dir = pathlib.Path(args.download_dir)
    sets_dir = pathlib.Path(args.sets_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    sets_dir.mkdir(parents=True, exist_ok=True)
    with open(args.countries_file, "r", encoding="utf-8") as f:
        countries = {line.strip().upper() for line in f if line.strip()}
    if not countries:
        (sets_dir / "geoip_ipv4.nft").write_text("define geoip_allowed_ipv4 = { }\n", encoding="utf-8")
        (sets_dir / "geoip_ipv6.nft").write_text("define geoip_allowed_ipv6 = { }\n", encoding="utf-8")
        return
    url = "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country-CSV&license_key=" + args.license_key + "&suffix=zip"
    archive_path = download_dir / "GeoLite2-Country-CSV.zip"
    urllib.request.urlretrieve(url, archive_path)
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="geoipcsv-"))
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(tmpdir)
        ipv4 = collect(list(tmpdir.rglob("*-Blocks-IPv4.csv")), countries)
        ipv6 = collect(list(tmpdir.rglob("*-Blocks-IPv6.csv")), countries)
        (sets_dir / "geoip_ipv4.nft").write_text("define geoip_allowed_ipv4 = { " + ", ".join(ipv4) + " }\n", encoding="utf-8")
        (sets_dir / "geoip_ipv6.nft").write_text("define geoip_allowed_ipv6 = { " + ", ".join(ipv6) + " }\n", encoding="utf-8")
    finally:
        shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
