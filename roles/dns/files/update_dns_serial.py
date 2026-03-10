#!/usr/bin/env python3
import argparse
import hashlib
import pathlib
import re

ap = argparse.ArgumentParser()
ap.add_argument("--zone-file", required=True)
args = ap.parse_args()

path = pathlib.Path(args.zone_file)
text = path.read_text(encoding="utf-8")
normalized = re.sub(r"^\s*\d{10}\s*$", "", text, flags=re.MULTILINE)
digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
serial = str(int(digest[:8], 16)).rjust(10, "0")[:10]
new_text = re.sub(r"(^\s*)\d{10}(\s*$)", "\\1" + serial + "\\2", text, count=1, flags=re.MULTILINE)
if new_text != text:
    path.write_text(new_text, encoding="utf-8")
