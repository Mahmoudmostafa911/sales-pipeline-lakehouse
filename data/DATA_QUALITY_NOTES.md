# Data-quality issues planted in the raw data

The generator (`generate_synthetic_data.py`) deliberately dirties the raw CSV files so the Silver step
has realistic problems to fix. Everything is synthetic.

| # | Issue | Where | Approx. volume | How the notebook handles it |
|---|-------|-------|----------------|-----------------------------|
| 1 | Exact duplicate rows | `opportunities.csv` | ~1 % | `dropDuplicates()` |
| 2 | Older versions of the same opportunity (same `opportunity_id`, older `last_modified_ts`) | `opportunities.csv` | ~0.5 % | keep the latest row per `opportunity_id` (`row_number` window) |
| 3 | Casing / whitespace in `stage` (`closed won`, `CLOSED LOST`, ` Proposal `, `Closed  Lost`) | `opportunities.csv` | ~3 % | `trim` + collapse spaces + `initcap` |
| 4 | Lower-case currency code (`usd`) | `opportunities.csv` | ~2 % | `upper(trim())` |
| 5 | Missing `amount` on open deals | `opportunities.csv` | ~1.5 % | kept as null (SUM ignores nulls) |
| 6 | Negative `amount` | `opportunities.csv` | ~0.3 % | moved to `silver_opportunities_quarantine` |
| 7 | `account_id` that does not exist in `accounts.csv` | `opportunities.csv` | ~0.5 % | moved to `silver_opportunities_quarantine` |
| 8 | Two date formats in `expected_close_date` (`2024-03-15` and `15/03/2024`) | `opportunities.csv` | ~2 % | `coalesce(to_date(ISO), to_date(dd/MM/yyyy))` |
| 9 | Activities logged before the opportunity was created | `activities.csv` | ~0.5 % | filtered out (`activity_ts >= created_date`) |

## Raw file summary (seed = 42)

| File | Rows | Grain |
|------|------|-------|
| `sellers.csv` | 40 | one row per seller |
| `accounts.csv` | 500 | one row per customer account |
| `opportunities.csv` | 3,045 (3,000 unique deals + planted duplicates) | one row per opportunity version |
| `opportunity_stage_history.csv` | ~11,300 | one row per stage transition |
| `activities.csv` | ~18,000 | one row per call / email / meeting / demo |

Snapshot date of the dataset: **2025-06-30**.

