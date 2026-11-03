"""Fetch a web page, save raw HTML and an extracted-text copy (for reading/citing).

Usage: .venv/bin/python -I scripts/capacity_storage/fetch_text.py <url> <out_basename> [--maxchars N]
Saves data/raw/capacity_storage/web/<out_basename>.html and .txt and prints the text.
"""
import os
import sys
import time

import requests
from bs4 import BeautifulSoup

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "capacity_storage", "web")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def main():
    url, base = sys.argv[1], sys.argv[2]
    maxc = int(sys.argv[sys.argv.index("--maxchars") + 1]) if "--maxchars" in sys.argv else 8000
    os.makedirs(OUT, exist_ok=True)
    r = requests.get(url, headers=UA, timeout=90)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "")
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        with open(os.path.join(OUT, base + ".pdf"), "wb") as f:
            f.write(r.content)
        print("saved pdf", len(r.content))
        return
    html = r.text
    with open(os.path.join(OUT, base + ".html"), "w", encoding="utf-8") as f:
        f.write(html)
    s = BeautifulSoup(html, "lxml")
    for t in s(["script", "style", "nav", "header", "footer", "noscript"]):
        t.decompose()
    node = s.find("article") or s.find("div", class_="innner-page-main-about-us-content-right-part") or s.body
    text = node.get_text("\n", strip=True)
    title = s.title.get_text(strip=True) if s.title else ""
    with open(os.path.join(OUT, base + ".txt"), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nTITLE: {title}\nFETCHED: {time.strftime('%Y-%m-%d')}\n\n{text}")
    print("TITLE:", title)
    print(text[:maxc])


if __name__ == "__main__":
    main()
