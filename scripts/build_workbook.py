"""Merge per-topic source registers and processed CSVs into deliverables, bucket-to-bucket.

Reads  s3://s1d-labs-trideep/from-box/india-renewable-power-research/{sources,processed}/...
Writes .../outputs/source_register.csv, dataset_index.csv, india_re_curtailment_data.xlsx
Nothing is written to local disk.  Run:  eval "$(mybucket env --box)"; .venv/bin/python -I scripts/build_workbook.py
"""
import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir from sys.path
from bucket import BUCKET, PREFIX, list_keys, read_csv, get_bytes, put_bytes
import pandas as pd

EXCEL_ROW_LIMIT = 150_000  # bigger block-level files stay CSV-only (Excel max 1,048,576; memory on the box is 6 GB)

regs = []
for k in list_keys("sources/"):
    if k.endswith("_sources.csv"):
        df = read_csv(k, dtype=str)
        df.insert(0, "topic", k.rsplit("/", 1)[-1].replace("_sources.csv", ""))
        regs.append(df)
register = pd.concat(regs, ignore_index=True) if regs else pd.DataFrame()
put_bytes("outputs/source_register.csv", register.to_csv(index=False).encode())

keys = [k for k in list_keys("processed/") if k.endswith((".csv", ".csv.gz"))
        and "/_" not in k]  # skip collectors' intermediate files (_work/, _*.csv)
index_rows, used = [], {"README", "source_register"}
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
    pd.DataFrame({"note": ["placeholder"]}).to_excel(xw, sheet_name="README", index=False)
    register.to_excel(xw, sheet_name="source_register", index=False)
    for k in keys:
        topic, fname = k.split("/")[-2], k.rsplit("/", 1)[-1]
        stem = fname.removesuffix(".gz").removesuffix(".csv")
        raw = get_bytes(k)
        comp = "gzip" if k.endswith(".gz") else None
        head = pd.read_csv(io.BytesIO(raw), compression=comp, nrows=5)
        n = sum(len(c) for c in pd.read_csv(io.BytesIO(raw), compression=comp, usecols=[0], chunksize=200_000))
        name = f"{topic[:4]}_{stem}"[:31]
        i = 1
        while name in used:
            name = f"{name[:28]}_{i}"
            i += 1
        fits = n <= EXCEL_ROW_LIMIT
        if fits:
            used.add(name)
            df = pd.read_csv(io.BytesIO(raw), compression=comp, low_memory=False)
            df.to_excel(xw, sheet_name=name, index=False)
            del df
        del raw
        index_rows.append({"topic": topic, "bucket_key": f"{PREFIX}{k}",
                           "sheet": name if fits else "(CSV only - too large for the workbook)",
                           "rows": n, "columns": ", ".join(map(str, head.columns))[:500]})
        print(f"{k}: {n} rows {'-> ' + name if fits else '(csv only)'}", flush=True)
    idx = pd.DataFrame(index_rows)
    idx.to_excel(xw, sheet_name="README", index=False)  # overwrite placeholder
put_bytes("outputs/india_re_curtailment_data.xlsx", buf.getvalue())
put_bytes("outputs/dataset_index.csv", idx.to_csv(index=False).encode())
print(f"register rows: {len(register)}; datasets: {len(idx)} -> s3://{BUCKET}/{PREFIX}outputs/")
