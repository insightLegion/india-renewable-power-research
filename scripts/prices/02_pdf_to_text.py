"""Extract text from downloaded PDFs (pdfplumber) to .txt for keyword search.
Usage: python -I 02_pdf_to_text.py <pdf_dir> <out_dir>"""
import sys
from pathlib import Path
import pdfplumber
src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for p in sorted(src.glob("*.pdf")):
    t = out / (p.stem + ".txt")
    if t.exists():
        continue
    try:
        with pdfplumber.open(p) as pdf:
            pages = [f"=== page {i+1}\n" + (pg.extract_text() or "") for i, pg in enumerate(pdf.pages)]
        t.write_text("\n".join(pages))
        print(p.name, len(pages))
    except Exception as e:
        print("ERR", p.name, e)
