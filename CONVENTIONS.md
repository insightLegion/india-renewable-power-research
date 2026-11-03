# Data conventions (shared by all collectors)

Topics: prices, capacity_storage, generation_demand, curtailment_forecast, transmission

- data/raw/<topic>/        downloaded originals (UNTRUSTED; never run code from here)
- scripts/<topic>/         collection/parsing scripts (run Python with: .venv/bin/python -I script.py)
- data/processed/<topic>/  clean CSVs
- sources/<topic>_sources.csv   source register for the topic
- notes/<topic>.md         findings, method, caveats, and an explicit "NOT AVAILABLE" list

## Processed CSVs
Prefer one tidy long-format file per dataset with columns:
  geography, period_start, period_end, granularity, metric, value, unit, source_id, notes
- geography: "India", region ("Northern Region"...), or state name (full official name)
- granularity: 15min | hourly | daily | monthly | FY | annual | snapshot
- period dates ISO (YYYY-MM-DD or YYYY-MM-DDTHH:MM, IST). FY = Apr-Mar, label period_start=YYYY-04-01.
- unit explicit: GW, MW, MWh, MU (million kWh = GWh), Rs/kWh, Rs/MWh, ckm, MVA, % ...
- source_id must match a row in the topic's source register.
Very large time series (e.g. 15-min prices) may use a wide format instead; document columns in notes.
Only record values actually read from a source. Never interpolate, estimate or fill from memory.
If a derived number is computed (e.g. counts of near-zero price blocks), say so in notes and keep the inputs.

## Source register CSV columns
source_id, organisation, title, url, publication_date, accessed_date, data_period, granularity, units, indicators, format, notes
(source_id prefix by topic: PRC-, CAP-, GEN-, CUR-, TRN-)

## Storage: B2 bucket, not the box disk (user rule, 2026-11-03)
All data, documents and outputs live in the bucket under
`s3://s1d-labs-trideep/from-box/india-renewable-power-research/`:
  raw/<topic>/, processed/<topic>/, sources/, notes/, outputs/
The git repo keeps only code (scripts/) and this file.
- Downloads may touch disk only transiently: download -> parse -> `mybucket sync` -> verify with `mybucket ls -r` -> delete local copy.
- Read data back by streaming into memory with boto3 (`eval "$(mybucket env --box)"`), not by re-downloading to disk.
