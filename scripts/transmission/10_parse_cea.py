"""Parse CEA transmission PDFs into tidy CSVs.

Outputs (data/processed/transmission/):
  transmission_capacity.csv   cumulative ckm by voltage (monthly, lines growth summaries),
                              cumulative MVA/MW by voltage (March + latest, substation growth summaries),
                              FY targets / achievements (executive summaries), ISTS vs intra-state FY additions
  inter_regional_capacity.csv inter-regional transmission capacity (MW), total and by corridor

Validation: each voltage group must satisfy Central+State+Private == Total and the grand total must equal the sum
of the voltage totals; rows failing validation are not written (reported on stdout).
"""
import csv, glob, os, re, subprocess, calendar
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data/raw/transmission")
OUT = os.path.join(ROOT, "data/processed/transmission")
os.makedirs(OUT, exist_ok=True)
NUM = re.compile(r"(?<![\w.,])\d{1,3}(?:,\d{2,3})+(?![\w,])|(?<![\w.,])\d+(?![\w,])")
VOLT = [("HVDC_800", r"±\s*800\s*kV"), ("HVDC_500", r"±\s*500\s*kV"), ("HVDC_320", r"±\s*320\s*kV"),
        ("765kV", r"\b765\s*kV"), ("400kV", r"\b400\s*kV"), ("220kV", r"\b220\s*kV")]
VLABEL = {"HVDC_800": "±800 kV HVDC", "HVDC_500": "±500 kV HVDC", "HVDC_320": "±320 kV HVDC",
          "765kV": "765 kV", "400kV": "400 kV", "220kV": "230/220 kV"}

def txt(f):
    return subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True).stdout

def nums(s):
    return [int(x.replace(",", "")) for x in NUM.findall(s)]

def month_end(p):
    y, m = map(int, p.split("-"))
    return f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

def fy_start(p):
    y, m = map(int, p.split("-"))
    return f"{y if m >= 4 else y - 1}-04-01"

rows = []
def add(geo, ps, pe, gran, metric, value, unit, sid, notes=""):
    rows.append(dict(geography=geo, period_start=ps, period_end=pe, granularity=gran, metric=metric,
                     value=value, unit=unit, source_id=sid, notes=notes))

def parse_growth(f, unit_metric, unit, sid, kind):
    """Return dict voltage->(C,S,P,T) and grand total for the last cumulative row of the commissioned table."""
    t = txt(f)
    volts = [v for v, rx in VOLT if re.search(rx, t)]
    nv = len(volts)
    cand = [l for l in t.splitlines() if len(nums(l)) >= 4 * nv + 1]
    if not cand:
        return None, "no rows"
    last = nums(cand[-1])
    # format A: groups of 4 per voltage + grand total by sector (4); format B: + single grand total
    for fmt, n in (("A", 4 * nv + 4), ("B", 4 * nv + 1)):
        if len(last) < n:
            continue
        v = last[-n:]
        groups = [v[4 * i:4 * i + 4] for i in range(nv)]
        if not all(g[0] + g[1] + g[2] == g[3] for g in groups):
            continue
        grand = v[-1]
        if sum(g[3] for g in groups) != grand:
            continue
        return dict(volts=volts, groups=groups, grand=grand, grand_sector=v[-4:] if fmt == "A" else None), "ok"
    return None, f"validation failed: {cand[-1].strip()[:120]}"

# ---------- A. cumulative lines (monthly) and substations (March + latest)
for kind, pat, metric, unit in (("lines", "lines_growth_*.pdf", "transmission_line_length_cumulative", "ckm"),
                                ("ss", "ss_growth_*.pdf", "transformation_capacity_cumulative", "MVA")):
    for f in sorted(glob.glob(os.path.join(RAW, "cea", pat))):
        p = re.search(r"(\d{4}-\d{2})", f).group(1)
        sid = f"TRN-CEA-{'LG' if kind == 'lines' else 'SG'}-{p}"
        r, msg = parse_growth(f, metric, unit, sid, kind)
        if not r:
            print("SKIP", os.path.basename(f), msg)
            continue
        pe = month_end(p)
        for v, g in zip(r["volts"], r["groups"]):
            u = unit
            if kind == "ss" and v.startswith("HVDC"):
                u = "MW"   # CEA reports HVDC terminal capacity in MW
            for sec, val in zip(("Central", "State", "Private/JV", "Total"), g):
                add("India", pe, pe, "snapshot", f"{metric}|{VLABEL[v]}|{sec}", val, u, sid,
                    "220 kV and above; cumulative as at month end")
        add("India", pe, pe, "snapshot", f"{metric}|All voltages|Total", r["grand"],
            "ckm" if kind == "lines" else "MVA+MW", sid,
            "220 kV and above; grand total" + ("; substations: AC MVA plus HVDC MW as summed by CEA" if kind == "ss" else ""))
        if r["grand_sector"]:
            for sec, val in zip(("Central", "State", "Private/JV"), r["grand_sector"][:3]):
                add("India", pe, pe, "snapshot", f"{metric}|All voltages|{sec}", val,
                    "ckm" if kind == "lines" else "MVA+MW", sid, "220 kV and above")

# ---------- B. FY target vs achievement (executive summaries)
for kind, pat, unit in (("lines", "lines_exec_*.pdf", "ckm"), ("ss", "ss_exec_*.pdf", "MVA")):
    for f in sorted(glob.glob(os.path.join(RAW, "cea", pat))):
        p = re.search(r"(\d{4}-\d{2})", f).group(1)
        sid = f"TRN-CEA-{'LE' if kind == 'lines' else 'SE'}-{p}"
        t = txt(f)
        target = ach = None
        head = " ".join(t.split()[:40]).lower()
        if (kind == "lines" and "transmission lines" not in head) or (kind == "ss" and "sub" not in head and "transformation" not in head):
            print("EXEC SKIP (wrong report type on CEA site)", os.path.basename(f)); continue
        m = [l for l in t.splitlines() if re.match(r"\s*GRAND TOTAL\b", l)]
        if m:
            n = nums(m[0])
            if len(n) >= 5:
                target, ach = n[0], n[4]
        else:
            prog = [l for l in t.splitlines() if re.match(r"\s*Programme\s+(FY\s*)?20\d\d", l)]
            achl = [l[re.search(r"Achievement", l).end():] for l in t.splitlines() if re.search(r"\bAchievement\s+\d", l)]
            ok = lambda n: len(n) >= 4 and n[-4] + n[-3] + n[-2] == n[-1]   # sector totals must add up
            if prog:
                n = nums(re.sub(r"Programme\s+(FY\s*)?20\d\d-\d\d", "", prog[0]))
                target = n[-1] if ok(n) else None
            if achl:
                n = nums(achl[-1])
                ach = n[-1] if ok(n) else None
        y, mm = map(int, p.split("-"))
        fs = fy_start(p)
        pe = month_end(p)
        lab = "transmission_lines" if kind == "lines" else "transformation_capacity"
        note = "220 kV and above; FY target (programme) as printed in the report" + ("" if mm == 3 else f"; FY in progress, achievement up to {pe}")
        if target is not None:
            add("India", fs, f"{int(fs[:4]) + 1}-03-31", "FY", f"{lab}_addition_target", target, unit, sid, note)
        if ach is not None:
            add("India", fs, pe, "FY", f"{lab}_addition_achieved", ach, unit, sid,
                "220 kV and above; achievement April to " + pe)
        print("EXEC", kind, p, target, ach)

# ---------- C. ISTS vs intra-state FY additions (latest lines growth summary)
latest = sorted(glob.glob(os.path.join(RAW, "cea", "lines_growth_*.pdf")))[-1]
lp = re.search(r"(\d{4}-\d{2})", latest).group(1)
sid = f"TRN-CEA-LG-{lp}"
t = txt(latest)
sec = t[t.find("Details of ISTS"):]
for l in sec.splitlines():
    m = re.match(r"\s*(20\d\d)-(\d\d)\b(.*)", l)
    if m:
        n = nums(m.group(3))
        if len(n) >= 3 and n[0] + n[1] == n[2]:
            fs = f"{m.group(1)}-04-01"
            pe = f"{int(m.group(1)) + 1}-03-31"
            note = "220 kV and above; FY additions"
            if m.group(1) == lp[:4] or (int(m.group(1)) == int(lp[:4]) - 1 and int(lp[5:]) < 4):
                pe = month_end(lp); note += f"; partial FY up to {pe}"
            for k, v in zip(("ISTS", "Intra-State", "Total"), n[:3]):
                add("India", fs, pe, "FY", f"transmission_line_addition|{k}", v, "ckm", sid, note)
for l in sec.splitlines():
    if re.search(r"As of 31st March (2004|2014)", l):
        n = nums(re.sub(r"As of 31st March \d{4}", "", l))
        yr = re.search(r"March (\d{4})", l).group(1)
        for k, v in zip(("ISTS", "Intra-State", "Total"), n[:3]):
            add("India", f"{yr}-03-31", f"{yr}-03-31", "snapshot", f"transmission_line_length_cumulative|{k}", v, "ckm", sid, "220 kV and above")
m = re.search(r"As of 30th\s*September.*?\n?.*?(\d{6})\s+(\d{6})\s+(\d{6})", sec)
blk = sec[sec.rfind("Period"):]
n = [x for x in nums(blk) if x > 100000]
if len(n) >= 3 and n[0] + n[1] == n[2]:
    for k, v in zip(("ISTS", "Intra-State", "Total"), n[:3]):
        add("India", month_end(lp), month_end(lp), "snapshot", f"transmission_line_length_cumulative|{k}", v, "ckm", sid, "220 kV and above")

with open(os.path.join(OUT, "transmission_capacity.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    seen = set()
    for r in rows:
        k = (r["period_start"], r["period_end"], r["metric"], r["source_id"])
        if k in seen:
            continue
        seen.add(k); w.writerow(r)
print("transmission_capacity rows", len(seen))

# ---------- D. inter-regional capacity
ir = []
CORR = ["ER-NR", "ER-WR", "WR-NR", "ER-SR", "WR-SR", "ER-NER", "NER-NR"]
def irrow(pe, gran, metric, val, sid, notes, ps=None):
    ir.append(dict(geography="India", period_start=ps or pe, period_end=pe, granularity=gran, metric=metric,
                   value=val, unit="MW", source_id=sid, notes=notes))

for f in sorted(glob.glob(os.path.join(RAW, "cea", "lines_growth_*.pdf"))):
    p = re.search(r"(\d{4}-\d{2})", f).group(1)
    t = txt(f)
    i = t.find("Inter- Regional") if "Inter- Regional" in t else t.find("Inter-Regional")
    if i < 0:
        continue
    sec = t[i:t.find("Details of ISTS", i) if "Details of ISTS" in t[i:] else None]
    data = [nums(l) for l in sec.splitlines()]
    data = [d for d in data if len(d) >= 8 and sum(d[-8:-1]) == d[-1]]
    if not data:
        print("IR SKIP", p); continue
    sid = f"TRN-CEA-LG-{p}"
    v = data[-1][-8:]
    pe = month_end(p)
    note = "220 kV and above; cumulative inter-regional transmission capacity as at month end (CEA growth summary)"
    irrow(pe, "snapshot", "inter_regional_capacity|Total", v[-1], sid, note)
    for c, x in zip(CORR, v[:7]):
        irrow(pe, "snapshot", f"inter_regional_capacity|{c}", x, sid, note)
    if p == lp:   # historical rows (plan ends and March values) from the latest report
        labels = []
        for l in sec.splitlines():
            n = nums(l)
            if len(n) >= 8 and sum(n[-8:-1]) == n[-1]:
                lab = re.sub(r"[\d,]+", "", l).strip()
                labels.append((lab, n[-8:]))
        hist = {"9th plan": "2002-03-31", "10th plan": "2007-03-31", "11th plan": "2012-03-31", "12th plan": "2017-03-31",
                "2017-2022": "2022-03-31"}
        march = ["2023-03-31", "2024-03-31", "2025-03-31", "2026-03-31"]
        mi = 0
        for lab, n in labels:
            key = lab.lower().split("(")[0].strip()
            if key in hist:
                d = hist[key]
            elif lab.startswith("Up to March"):
                d = march[mi]; mi += 1
            else:
                continue
            nn = f"as printed in CEA growth summary {lp}: row '{lab}'"
            irrow(d, "snapshot", "inter_regional_capacity|Total", n[-1], sid, nn)
            for c, x in zip(CORR, n[:7]):
                irrow(d, "snapshot", f"inter_regional_capacity|{c}", x, sid, nn)

# March totals from CEA power-sector Executive Summaries
for f in sorted(glob.glob(os.path.join(RAW, "cea_es", "es_*.pdf"))):
    p = re.search(r"(\d{4}-\d{2})", f).group(1)
    sid = f"TRN-CEA-ES-{p}"
    t = txt(f)
    val = None
    m = re.search(r"Inter-regional\s*\n\s*transmission\s+MW\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", t)
    if m:
        val = int(m.group(3).replace(",", ""))
        note = "CEA Executive Summary 'Growth of Transmission Sector' table, column 'Ach. as on' report date"
    else:
        i = t.find("Inter-regional Power Transfer Capacity")
        if i < 0:
            i = t.find("Inter-regional Transmission Capacity")
        if i >= 0:
            blk = t[i:i + 3000]
            cands = re.findall(r"(\d{1,3}(?:,\d{2,3})+|\d{5,6})\*", blk)
            if cands:
                val = int(cands[-1].replace(",", ""))
                note = "CEA Executive Summary: cumulative inter-regional capacity value marked * (excludes 600 MW of 132 kV links operated radially)"
    if val:
        irrow(month_end(p), "snapshot", "inter_regional_capacity|Total", val, sid, note)
        print("ES IR", p, val)

with open(os.path.join(OUT, "inter_regional_capacity.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(ir[0].keys()))
    w.writeheader(); w.writerows(ir)
print("inter_regional rows", len(ir))
