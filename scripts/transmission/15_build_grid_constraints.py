"""Merge constraint items into data/processed/transmission/grid_constraints.csv.

Inputs:
  _qof_constraints.csv   (14_parse_qof.py: NLDC quarterly operational feedback, table rows + RE-specific section headings)
  _tgna_constraints.csv  (12_parse_tgna_margin.py: 'Limiting Constraints' text per ISTS RE complex per issue)
T-GNA items are collapsed to one row per (complex, constraint text) with first/last issue date seen.
Columns: period_start, period_end, quarter, region, state, element, constraint_type, description, re_related, source_id, notes
"""
import csv, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, "data/processed/transmission")
STATES = ["Rajasthan", "Gujarat", "Karnataka", "Andhra Pradesh", "Tamil Nadu", "Maharashtra", "Madhya Pradesh", "Uttar Pradesh", "Punjab", "Haryana",
          "Delhi", "Odisha", "Bihar", "West Bengal", "Jharkhand", "Kerala", "Telangana", "Chhattisgarh", "Himachal", "Uttarakhand", "Assam", "Goa"]
out = []
def q_label(ps):
    y, m = int(ps[:4]), int(ps[5:7])
    fy = y if m >= 4 else y - 1
    q = {4: 1, 7: 2, 10: 3, 1: 4}[m]
    return f"FY{fy}-{str(fy + 1)[2:]} Q{q}"

for r in csv.DictReader(open(os.path.join(P, "_qof_constraints.csv"))):
    txt = r["element"] + " " + r["description"]
    st = ";".join(s for s in STATES if s.lower() in txt.lower())
    reg = re.sub(r"\s+", " ", r["region"]).replace("North- Eastern", "North-Eastern").replace("North Eastern", "North-Eastern")
    out.append(dict(period_start=r["period_start"], period_end=r["period_end"], quarter=q_label(r["period_start"]), region=reg, state=st,
                    element=r["element"], constraint_type=r["constraint_type"], description=r["description"], re_related=r["re_related"],
                    source_id=r["source_id"], notes=f"NLDC quarterly operational feedback issued {r['report']}; re_related is a keyword flag"))

tg = {}
for r in csv.DictReader(open(os.path.join(P, "_tgna_constraints.csv"))):
    k = (r["area"], r["text"])
    if k not in tg:
        tg[k] = dict(first=r["date"], last=r["date"], region=r["region"], pooling=r["pooling"], n=1)
    else:
        tg[k]["first"] = min(tg[k]["first"], r["date"]); tg[k]["last"] = max(tg[k]["last"], r["date"]); tg[k]["n"] += 1
for (area, text), v in sorted(tg.items(), key=lambda x: (x[0][0], x[1]["first"])):
    st = "Rajasthan" if "Rajasthan" in area else "Gujarat" if ("Gujarat" in area or "Khavda" in area) else ""
    out.append(dict(period_start=v["first"], period_end=v["last"], quarter="", region=v["region"], state=st, element=f"{area} (pooling stations: {v['pooling'][:150]})",
                    constraint_type="limiting constraint for RE evacuation (T-GNA margin)", description=text[:1500], re_related="yes", source_id="TRN-GI-TGNA",
                    notes=f"text identical in {v['n']} T-GNA margin issues between {v['first']} and {v['last']}"))

with open(os.path.join(P, "grid_constraints.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("rows", len(out), "re-related", sum(o["re_related"] == "yes" for o in out))
