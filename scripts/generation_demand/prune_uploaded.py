"""Delete local raw files that are confirmed in the B2 bucket (same key, same size).

Usage: eval "$(mybucket env --box)"; .venv/bin/python -I scripts/generation_demand/prune_uploaded.py LOCAL_DIR BUCKET_PREFIX [--only-parsed]
  --only-parsed : for daily_psp_report, delete only files already recorded in _work/psp_parse_log.csv
Prints counts; never deletes a file whose bucket copy is missing or differs in size.
"""
import os
import sys
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[2]
local = Path(sys.argv[1]).resolve()
prefix = sys.argv[2].rstrip("/") + "/"
only_parsed = "--only-parsed" in sys.argv

env = os.environ
s3 = boto3.client("s3", endpoint_url=env.get("AWS_ENDPOINT_URL") or env.get("B2_ENDPOINT") or env.get("S3_ENDPOINT"))
bucket = env.get("B2_BUCKET") or env.get("BUCKET") or "s1d-labs-trideep"
remote = {}
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
    for o in page.get("Contents", []):
        remote[o["Key"][len(prefix):]] = o["Size"]

parsed = None
if only_parsed:
    import csv
    parsed = {r["file"] for r in csv.DictReader((ROOT / "data/processed/generation_demand/_work/psp_parse_log.csv").open())}

deleted = kept = 0
for p in sorted(local.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(local).as_posix()
    if parsed is not None and p.name not in parsed:
        kept += 1
        continue
    if remote.get(rel) == p.stat().st_size:
        p.unlink()
        deleted += 1
    else:
        kept += 1
print(f"bucket objects under prefix: {len(remote)}; deleted {deleted}; kept {kept}")
