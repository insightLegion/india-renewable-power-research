"""Project-level status of under-construction ISTS (TBCB) transmission projects, CEA monthly report (Sep 2026).

Input: data/raw/transmission/plans/cea_tbcb_underconstruction_2026-09.pdf
Output: data/processed/transmission/_tbcb_projects.csv (merged into re_transmission_plans.csv by 18_build_re_plans.py)
Per project: name, executing agency, cost (Rs crore), SPV transfer date, original completion target, anticipated completion,
DERIVED delay_months = anticipated - original (computed here), re_zone flag (keyword match on project name).
"""
import csv, os, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = os.path.join(ROOT, "data/raw/transmission/plans/cea_tbcb_underconstruction_2026-09.pdf")
OUT = os.path.join(ROOT, "data/processed/transmission/_tbcb_projects.csv")
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
AG = r"(PGCIL|Sterlite|Adani|Tata Power|Indigrid|GR Infra|Apraava Energy|Torrent|Techno Electric|DRAIPL|Reliance|HGIEL|SCL)"
HDR = re.compile(r"^\s*(\d{1,3})\s+(.+)\s+" + AG + r"\s+([\d,]+)\s+([A-Z][a-z]{2}-\d\d)\s+([A-Z][a-z]{2}-\d\d)\s+([A-Z][a-z]{2})\s*-\s*(\d\d)")
RE_KW = re.compile(r"\bRE\b|REZ|Renewable|solar|wind|Khavda|Fatehgarh|Bhadla|Bikaner|Barmer|Ramgarh|Koppal|Gadag|Kurnool|Ananthapur|"
                   r"Bidar|Tumkur|Davanagere|Krishnagiri|Bijapur|Dhule|Kallam|Raghanesda|Banaskantha|Jam Khambhaliya|KPS|Lakadia|Navinal", re.I)

def mi(s):
    m, y = s.split("-")
    return (2000 + int(y)) * 12 + MON[m[:3].lower()] - 1

lines = subprocess.run(["pdftotext", "-layout", F, "-"], capture_output=True, text=True).stdout.splitlines()
rows = []
for i, l in enumerate(lines):
    m = HDR.match(l)
    if not m:
        continue
    name = re.sub(r"\s+", " ", m.group(2)).strip()
    if int(m.group(1)) > 150 or name.startswith("kV"):   # element lines starting with a voltage, not project headers
        continue
    # continuation of the project name: following lines up to the first scope line (which repeats the agency)
    for nl in lines[i + 1:i + 4]:
        if m.group(3) in nl or not nl.strip() or HDR.match(nl):
            break
        name += " " + re.sub(r"\s+", " ", nl).strip()
    orig, anti = m.group(6), f"{m.group(7)}-{m.group(8)}"
    rows.append(dict(sl=m.group(1), project=name[:300], agency=m.group(3).strip(), cost_rs_crore=m.group(4).replace(",", ""),
                     spv_transfer=m.group(5), completion_original=orig, completion_anticipated=anti,
                     delay_months=mi(anti) - mi(orig), re_zone="yes" if RE_KW.search(name) else "no",
                     state_hint=";".join(sorted(set(x for x in ("Rajasthan", "Gujarat", "Karnataka", "Andhra", "Maharashtra", "Tamil Nadu", "Madhya Pradesh", "Khavda")
                                                    if x.lower() in name.lower())))))
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "projects;", sum(r["re_zone"] == "yes" for r in rows), "RE-zone")
for r in rows[:5]: print(r)
