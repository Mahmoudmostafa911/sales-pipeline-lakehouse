# Deploying to Microsoft Fabric

The notebooks in this repo are platform-agnostic: on Fabric they auto-detect the attached Lakehouse
(`/lakehouse/default`) and read/write through the `Files/` and `Tables/` shortcuts. This guide covers the
Fabric-specific pieces around them — workspace setup, orchestration with a Data Pipeline, and the Direct Lake
semantic model.

## 1. Workspace and Lakehouse

1. In a Fabric-enabled workspace create a **Lakehouse** named `SalesPipelineLH`.
2. In the Lakehouse explorer, under **Files**, create the folder `raw` and upload the five CSV files from
   `data/raw/` (or use a *Get data → Upload files* step).
3. Import the three notebooks (`Workspace → Import → Notebook`) and, in each one, **add the Lakehouse as the
   default Lakehouse** (left pane → *Add Lakehouse* → existing). The configuration cell then resolves
   `RAW_PATH = "Files/raw"` and writes Delta tables to `Tables/`.

Run `01_bronze_ingest` once manually to confirm the tables appear under **Tables** in the Lakehouse.

## 2. Orchestration — Data Pipeline

Create a **Data Pipeline** named `pl_sales_lakehouse_daily`:

```
[Copy data]  ──►  [Notebook: 01_bronze_ingest]  ──►  [Notebook: 02_silver_clean_conform]  ──►  [Notebook: 03_gold_star_schema]
  (optional)            on success                       on success                              on success
                                                          │ on failure
                                                          └──► [Office 365 Outlook: send failure e-mail]
```

* **Copy data** (optional): if the CSVs come from a source system (SharePoint, ADLS, SFTP, a database), a Copy
  activity lands them into `Files/raw`, replacing the manual upload.
* **Notebook activities**: one per notebook, chained with *On success*. Set the workspace and notebook, leave
  parameters empty — the notebooks detect Fabric automatically.
* **Failure branch**: the Silver notebook raises `RuntimeError` when any data-quality check is `FAIL`, which fails
  the activity and stops Gold from running. Wire the *On failure* output to an **Office 365 Outlook** (or Teams)
  activity to notify the data owner.
* **Schedule**: daily at 06:00 local time (Pipeline → Schedule).

### Parameterising the notebooks (optional)
Turn the first code cell of each notebook into a **parameter cell** (cell menu → *Toggle parameter cell*) and pass
`PLATFORM`, `SCHEMA` or a `SNAPSHOT_DATE` from the pipeline's *Base parameters*. This lets the same notebook serve
dev/test/prod Lakehouses.

## 3. Semantic model — Direct Lake

1. Open the Lakehouse → **New semantic model** → select the eight `gold_*` tables.
2. In the model view create the relationships listed in `model/dax_measures.md` (mark `gold_dim_date` as the
   date table; set the close-date relationship to inactive).
3. Add the measures from `model/dax_measures.md` into a `_Measures` table.
4. Add the RLS role and the `Region Access` mapping table (as a Lakehouse table so it is governed with the data).
5. Create the report from the model using `model/report_layout.md`.

Direct Lake reads the Delta files directly, so there is no import refresh: when the pipeline rewrites the Gold
tables the model reflects them on the next query (framing). Keep the Gold tables `OPTIMIZE`d and V-Ordered
(default in Fabric) for best Direct Lake performance.

## 4. Monitoring

* **Monitoring hub** shows every pipeline and notebook run with duration and status.
* `silver_dq_results` is itself a Lakehouse table — add it to the semantic model for a *Data Quality* report page,
  or set up a **Data Activator** alert on `status = "FAIL"`.
* Use the Lakehouse **SQL analytics endpoint** for ad-hoc T-SQL over the Gold tables
  (`SELECT * FROM gold_fact_opportunity WHERE is_closed = 0`).

## 5. Differences from the Databricks / local run

| Concern | Databricks / local | Fabric |
|---|---|---|
| Storage | Unity Catalog volume / local folder | OneLake `Files/` |
| Table namespace | `catalog.schema.table` / `schema.table` | Lakehouse `Tables` (single namespace) |
| Orchestration | Databricks Workflow / manual | Data Pipeline |
| Power BI connectivity | Import from export or Databricks connector | **Direct Lake** (no export step) |
| Ad-hoc SQL | Databricks SQL | SQL analytics endpoint (T-SQL) |

Everything inside the notebooks — PySpark transformations, Delta MERGE, OPTIMIZE, time travel, the star schema —
is identical across all three platforms.
