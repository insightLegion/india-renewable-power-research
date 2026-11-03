"""Zip ALL project sources (raw source documents, processed data, register, notes, outputs, code) into one
zip in the bucket, streaming: each object is read into memory and written into a zip whose bytes are sent as
S3 multipart parts. Nothing is written to the box disk.

Run:  eval "$(mybucket env --box)"; .venv/bin/python -I scripts/zip_all_sources.py
"""
import sys
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bucket import BUCKET, PREFIX, s3, list_keys, get_bytes

ROOT = Path(__file__).resolve().parents[1]
ZIP_KEY = f"{PREFIX}zip/india-renewable-power-research_all-sources_{date.today():%Y-%m-%d}.zip"
PART = 100 * 1024 * 1024


class MultipartWriter:
    """Unseekable file-like object that uploads to S3 in 100 MB parts."""

    def __init__(self, key):
        self.key, self.buf, self.parts, self.pos = key, bytearray(), [], 0
        self.uid = s3.create_multipart_upload(Bucket=BUCKET, Key=key, ContentType="application/zip")["UploadId"]
        self.pool = ThreadPoolExecutor(3)  # parts upload in the background (max ~3 x 100 MB in flight)
        self.futs = []

    def write(self, b):
        self.buf += b
        self.pos += len(b)
        while len(self.buf) >= PART:
            self._send(bytes(self.buf[:PART]))
            del self.buf[:PART]
        return len(b)

    def tell(self):
        return self.pos

    def flush(self):
        pass

    def _send(self, data):
        n = len(self.futs) + 1
        while sum(not f.done() for f in self.futs) >= 3:
            self.futs[[i for i, f in enumerate(self.futs) if not f.done()][0]].result()
        self.futs.append(self.pool.submit(self._up, n, data))

    def _up(self, n, data):
        r = s3.upload_part(Bucket=BUCKET, Key=self.key, PartNumber=n, UploadId=self.uid, Body=data)
        return {"PartNumber": n, "ETag": r["ETag"]}

    def close(self):
        if self.buf:
            self._send(bytes(self.buf))
        self.parts = [f.result() for f in self.futs]
        s3.complete_multipart_upload(Bucket=BUCKET, Key=self.key, UploadId=self.uid,
                                     MultipartUpload={"Parts": self.parts})

    def abort(self):
        s3.abort_multipart_upload(Bucket=BUCKET, Key=self.key, UploadId=self.uid)


keys = [k for k in list_keys("") if not k.startswith("zip/")]
code = [p for p in ROOT.rglob("*") if p.is_file() and not any(
    part in {".git", ".venv", "__pycache__", ".playwright-mcp", "data"} for part in p.relative_to(ROOT).parts)]
w = MultipartWriter(ZIP_KEY)
total = 0
try:
    with zipfile.ZipFile(w, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        fetch = ThreadPoolExecutor(16)
        window = deque(fetch.submit(get_bytes, k) for k in keys[:24])
        nxt = 24
        for i, k in enumerate(keys, 1):
            data = window.popleft().result()
            if nxt < len(keys):
                window.append(fetch.submit(get_bytes, keys[nxt]))
                nxt += 1
            total += len(data)
            # PDFs/zips/xlsx/images are already compressed: store them
            stored = k.lower().endswith((".pdf", ".zip", ".xlsx", ".png", ".jpg", ".gz", ".xls", ".docx"))
            z.writestr(zipfile.ZipInfo(f"india-renewable-power-research/{k}", date_time=(2026, 11, 3, 0, 0, 0)),
                       data, compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED)
            if i % 500 == 0:
                print(f"{i}/{len(keys)} objects, {total/1e9:.2f} GB read", flush=True)
        for p in code:
            z.write(p, f"india-renewable-power-research/code/{p.relative_to(ROOT)}")
    w.close()
except BaseException:
    w.abort()
    raise
print(f"done: {len(keys)} bucket objects + {len(code)} code files, {total/1e9:.2f} GB in -> s3://{BUCKET}/{ZIP_KEY}")
