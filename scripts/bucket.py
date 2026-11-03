"""Tiny helpers to read/write project files in the B2 bucket without touching local disk.

Needs credentials in env:  eval "$(mybucket env --box)"
"""
import io
import os
import boto3
import pandas as pd

BUCKET = os.environ.get("S3_BUCKET") or os.environ.get("B2_BUCKET") or "s1d-labs-trideep"
PREFIX = "from-box/india-renewable-power-research/"


def _client():
    kw = {}
    ep = os.environ.get("AWS_ENDPOINT_URL") or os.environ.get("B2_ENDPOINT") or os.environ.get("S3_ENDPOINT")
    if ep:
        kw["endpoint_url"] = ep if ep.startswith("http") else f"https://{ep}"
    return boto3.client("s3", **kw)


s3 = _client()


def list_keys(sub: str) -> list[str]:
    """Keys (relative to PREFIX) under PREFIX+sub."""
    out, tok = [], None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": PREFIX + sub}
        if tok:
            kw["ContinuationToken"] = tok
        r = s3.list_objects_v2(**kw)
        out += [o["Key"][len(PREFIX):] for o in r.get("Contents", [])]
        if not r.get("IsTruncated"):
            return sorted(out)
        tok = r["NextContinuationToken"]


def get_bytes(key: str) -> bytes:
    return s3.get_object(Bucket=BUCKET, Key=PREFIX + key)["Body"].read()


def read_csv(key: str, **kw) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(get_bytes(key)), **kw)


def put_bytes(key: str, data: bytes) -> None:
    s3.put_object(Bucket=BUCKET, Key=PREFIX + key, Body=data)
