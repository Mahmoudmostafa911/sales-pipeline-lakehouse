# Sales Pipeline Lakehouse (Microsoft Fabric)

A small end-to-end project I built to practise the Fabric data-engineering flow:
raw CSV files -> Lakehouse (bronze / silver / gold Delta tables) -> star schema for Power BI.

The data is synthetic (generated with `data/generate_synthetic_data.py`) and looks like a CRM export:
sellers, accounts, opportunities, stage history and activities. It contains the usual real-life problems
on purpose: duplicated rows, inconsistent casing, mixed date formats, missing and negative amounts, orphan keys.

## The notebook

`notebooks/sales_pipeline_lakehouse.ipynb` - one PySpark notebook, three steps:

| Layer | Tables | What happens |
|---|---|---|
| Bronze | `bronze_*` | the 5 CSV files are loaded as-is (all text) into Delta tables, with a load timestamp |
| Silver | `silver_*` | proper data types, trimmed / title-cased text, two date formats handled, exact duplicates removed and only the latest version of each opportunity kept, rows with a negative amount or an unknown account moved to `silver_opportunities_quarantine` |
| Gold | `dim_*`, `fact_*` | star schema: `dim_date` (fiscal year starting in July), `dim_seller`, `dim_account`, `dim_stage`, `fact_opportunity`, `fact_stage_history` (days spent in each stage), `fact_activity` |

## How to run it in Fabric

1. Create a Lakehouse in your workspace.
2. In the Lakehouse, create the folder `Files/raw` and upload the five CSV files from `data/raw`.
3. Import `notebooks/sales_pipeline_lakehouse.ipynb` (Workspace -> Import -> Notebook) and attach the Lakehouse to it.
4. Run all cells. The last two cells show deals and amount per stage and the quarantined rows.
5. Build the Power BI report on the `dim_*` and `fact_*` tables. Relationships and measures are in `model/dax_measures.md`.

## Raw data

| File | Rows | Grain |
|---|---|---|
| `sellers.csv` | 40 | one row per seller |
| `accounts.csv` | 500 | one row per customer account |
| `opportunities.csv` | 3,045 | one row per opportunity version (3,000 unique deals + planted duplicates) |
| `opportunity_stage_history.csv` | ~11,300 | one row per stage change |
| `activities.csv` | ~18,000 | one row per call / email / meeting / demo |

Snapshot date of the data: 2025-06-30. The data-quality problems planted in the files are listed in `data/DATA_QUALITY_NOTES.md`.

## Tools

Microsoft Fabric (Lakehouse, Notebook, Delta Lake) · PySpark · Spark SQL · Power BI · DAX

