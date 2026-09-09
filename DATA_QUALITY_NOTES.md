# Data-quality issues planted in the raw data

The generator (`generate_synthetic_data.py`) deliberately dirties the raw CSVs so the
Silver notebook has realistic problems to detect and fix. Everything is synthetic.

| # | Issue | Where | Approx. volume | How Silver handles it |
|---|-------|-------|----------------|-----------------------|
| 1 | Exact duplicate rows | `opportunities.csv` | ~1 % | `dropDuplicates()` on business columns |
| 2 | Stale duplicate versions (same `opportunity_id`, older `last_modified_ts`, earlier stage) | `opportunities.csv` | ~0.5 % | keep latest per `opportunity_id` with a `row_number()` window |
| 3 | Inconsistent casing / whitespace in `stage` (`closed won`, `CLOSED LOST`, ` Proposal `, `Closed  Lost`) | `opportunities.csv` | ~3 % | trim, collapse whitespace, Title-Case (`clean_label`) |
| 4 | Lower-case currency code (`usd`) | `opportunities.csv` | ~2 % | `upper(trim())` |
| 5 | Missing `amount` on open deals | `opportunities.csv` | ~1.5 % | kept, flagged `amount_missing = true` (SUM ignores nulls) |
| 6 | Negative `amount` (data-entry error) | `opportunities.csv` | ~0.3 % | routed to `silver_opportunities_quarantine` |
| 7 | Orphan `account_id` (account does not exist) | `opportunities.csv` | ~0.5 % | referential-integrity check → quarantine |
| 8 | Mixed date formats in `expected_close_date` (ISO and `dd/MM/yyyy`) | `opportunities.csv` | ~2 % | multi-format parser with `try_to_timestamp` |
| 9 | Activities logged before the opportunity was created | `activities.csv` | ~0.5 % | temporal check → `silver_activities_quarantine` |

Every check writes a row to `silver_dq_results` (check name, table, failed rows,
total rows, PASS/WARN, run timestamp) so data quality is observable over time.

## Raw file summary (seed = 42)

| File | Rows | Grain |
|------|------|-------|
| `sellers.csv` | 40 | one row per seller |
| `accounts.csv` | 500 | one row per customer account |
| `opportunities.csv` | 3,045 (3,000 unique deals + planted duplicates) | one row per opportunity version |
| `opportunity_stage_history.csv` | ~11,300 | one row per stage transition |
| `activities.csv` | ~18,000 | one row per call / email / meeting / demo |

Snapshot date of the dataset: **2025-06-30**.
