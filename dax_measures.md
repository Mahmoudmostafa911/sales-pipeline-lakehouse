# Semantic model — tables, relationships and DAX measures

The model sits directly on the Gold star schema. In **Fabric** it is a Direct Lake model over the
Lakehouse tables; without a capacity it is an **Import** model in Power BI Desktop built from the
CSV/Parquet export produced by notebook 03. The DAX is identical in both cases.

Save the model as a **`.pbip` project** (File → Options → Preview features → *Power BI Project (.pbip) save option*)
so the model definition (TMDL) and the DAX live as readable text files in this repo under `model/`.

## 1. Tables and relationships

```
gold_dim_date[date_key]        1 ──< *  gold_fact_opportunity[created_date_key]        (active)
gold_dim_date[date_key]        1 ──< *  gold_fact_opportunity[actual_close_date_key]   (inactive – used via USERELATIONSHIP)
gold_dim_date[date_key]        1 ──< *  gold_fact_stage_transition[changed_date_key]   (active)
gold_dim_date[date_key]        1 ──< *  gold_fact_activity[activity_date_key]          (active)
gold_dim_seller[seller_key]    1 ──< *  gold_fact_opportunity[seller_key]
gold_dim_seller[seller_key]    1 ──< *  gold_fact_stage_transition[seller_key]
gold_dim_seller[seller_key]    1 ──< *  gold_fact_activity[seller_key]
gold_dim_account[account_key]  1 ──< *  gold_fact_opportunity[account_key]
gold_dim_product[product_key]  1 ──< *  gold_fact_opportunity[product_key]
gold_dim_stage[stage_key]      1 ──< *  gold_fact_opportunity[stage_key]
gold_dim_stage[stage_key]      1 ──< *  gold_fact_stage_transition[to_stage_key]       (active)
gold_dim_stage[stage_key]      1 ──< *  gold_fact_stage_transition[from_stage_key]     (inactive)
```

Settings worth applying:

* Mark `gold_dim_date` as the **date table** (`date` column).
* Single-direction filters everywhere; no bi-directional relationships.
* Hide every `*_key` column and the fact tables' technical columns (`amount_missing`, `activity_minutes`) from report view.
* Sort `month_name` by `month`, `fiscal_period` by a `fiscal_period_sort` column if you add one (`fiscal_year * 10 + fiscal_quarter`).
* Rename tables in the model without the `gold_` prefix (`Opportunity`, `Seller`, `Account`, `Date`, `Stage`, `Product`,
  `Stage Transition`, `Activity`) — the DAX below uses those display names.

## 2. Core measures (table `_Measures`)

```dax
-- ---------- Pipeline ----------
Open Pipeline =
CALCULATE ( SUM ( Opportunity[amount] ), Opportunity[is_closed] = FALSE () )

Weighted Pipeline =
CALCULATE ( SUM ( Opportunity[weighted_amount] ), Opportunity[is_closed] = FALSE () )

Open Opportunities =
CALCULATE ( COUNTROWS ( Opportunity ), Opportunity[is_closed] = FALSE () )

Average Open Deal Size =
DIVIDE ( [Open Pipeline], [Open Opportunities] )

Average Days Open =
CALCULATE ( AVERAGE ( Opportunity[days_open] ), Opportunity[is_closed] = FALSE () )

-- ---------- Outcomes (by close date) ----------
Won Revenue =
CALCULATE (
    SUM ( Opportunity[amount] ),
    Opportunity[is_won] = TRUE (),
    USERELATIONSHIP ( Opportunity[actual_close_date_key], 'Date'[date_key] )
)

Won Deals =
CALCULATE (
    COUNTROWS ( Opportunity ),
    Opportunity[is_won] = TRUE (),
    USERELATIONSHIP ( Opportunity[actual_close_date_key], 'Date'[date_key] )
)

Lost Deals =
CALCULATE (
    COUNTROWS ( Opportunity ),
    Opportunity[is_closed] = TRUE (), Opportunity[is_won] = FALSE (),
    USERELATIONSHIP ( Opportunity[actual_close_date_key], 'Date'[date_key] )
)

Closed Deals = [Won Deals] + [Lost Deals]

Win Rate = DIVIDE ( [Won Deals], [Closed Deals] )

Average Won Deal Size = DIVIDE ( [Won Revenue], [Won Deals] )

Average Sales Cycle (Days) =
CALCULATE (
    AVERAGE ( Opportunity[sales_cycle_days] ),
    Opportunity[is_won] = TRUE (),
    USERELATIONSHIP ( Opportunity[actual_close_date_key], 'Date'[date_key] )
)

-- ---------- Quota & coverage ----------
Quota =
SUM ( Seller[quota_annual] )

Quota Attainment % =
DIVIDE ( [Won Revenue], [Quota] )

Remaining Quota =
MAX ( 0, [Quota] - [Won Revenue] )

Pipeline Coverage =
DIVIDE ( [Open Pipeline], [Remaining Quota] )
-- 3x is the usual healthy benchmark; format as "0.0x"

-- ---------- Seller productivity ----------
Active Sellers =
CALCULATE ( DISTINCTCOUNT ( Opportunity[seller_key] ), Opportunity[is_closed] = TRUE () )

Won Revenue per Seller = DIVIDE ( [Won Revenue], [Active Sellers] )

Won Deals per Seller = DIVIDE ( [Won Deals], [Active Sellers] )

Activities = COUNTROWS ( Activity )

Activities per Won Deal = DIVIDE ( [Activities], [Won Deals] )

Meetings & Demos =
CALCULATE ( COUNTROWS ( Activity ), Activity[activity_type] IN { "Meeting", "Demo" } )

-- ---------- Time intelligence (Date table required) ----------
Won Revenue YTD = TOTALYTD ( [Won Revenue], 'Date'[date] )

Won Revenue FYTD = TOTALYTD ( [Won Revenue], 'Date'[date], "06-30" )   -- July fiscal year

Won Revenue PY = CALCULATE ( [Won Revenue], SAMEPERIODLASTYEAR ( 'Date'[date] ) )

Won Revenue YoY % = DIVIDE ( [Won Revenue] - [Won Revenue PY], [Won Revenue PY] )

Won Revenue Rolling 3M =
CALCULATE ( [Won Revenue], DATESINPERIOD ( 'Date'[date], MAX ( 'Date'[date] ), -3, MONTH ) )
```

## 3. Funnel / conversion measures (table `Stage Transition`)

```dax
Stage Entries =
COUNTROWS ( 'Stage Transition' )                     -- rows entering the stage in the active (to_stage) relationship

Stage Exits =
CALCULATE (
    COUNTROWS ( 'Stage Transition' ),
    USERELATIONSHIP ( 'Stage Transition'[from_stage_key], Stage[stage_key] )
)

Stage Conversion % =
-- share of deals that entered the selected stage and later moved to ANY next stage
DIVIDE ( [Stage Exits], [Stage Entries] )

Advance Rate % =
-- share of exits that moved forward (not to Closed Lost)
VAR _exits = [Stage Exits]
VAR _lost =
    CALCULATE (
        COUNTROWS ( 'Stage Transition' ),
        USERELATIONSHIP ( 'Stage Transition'[from_stage_key], Stage[stage_key] ),
        'Stage Transition'[to_stage] = "Closed Lost"
    )
RETURN DIVIDE ( _exits - _lost, _exits )

Average Days in Stage =
CALCULATE (
    AVERAGE ( 'Stage Transition'[days_in_from_stage] ),
    USERELATIONSHIP ( 'Stage Transition'[from_stage_key], Stage[stage_key] )
)

Deals Reaching Stage =
CALCULATE ( DISTINCTCOUNT ( 'Stage Transition'[opportunity_id] ) )
```

## 4. Data-quality measures (optional, table `silver_dq_results` imported as `Data Quality`)

```dax
DQ Checks = COUNTROWS ( 'Data Quality' )
DQ Failed Rows = SUM ( 'Data Quality'[failed_rows] )
DQ Pass Rate % =
DIVIDE ( CALCULATE ( COUNTROWS ( 'Data Quality' ), 'Data Quality'[status] = "PASS" ), [DQ Checks] )
```

## 5. Row-level security

Role **Regional Sales Leader** — one filter on `Seller`:

```dax
[region] = LOOKUPVALUE ( 'Region Access'[region], 'Region Access'[user_upn], USERPRINCIPALNAME () )
```

where `Region Access` is a small two-column mapping table (`user_upn`, `region`). Because `Seller`
filters every fact table, one rule secures pipeline, transitions and activities at once.

## 6. Formatting

| Measure | Format |
|---|---|
| Revenue / pipeline amounts | `$#,0,,.0M` (or `#,0` for detail tables) |
| Win Rate, Attainment, Conversion | `0.0%` |
| Pipeline Coverage | `0.0"x"` |
| Days | `#,0` |

## 7. Reconciliation checkpoints

Notebook 03 prints these totals with Spark SQL — the model must match them at the grand-total level
(no filters):

| Check | Spark SQL column | DAX measure |
|---|---|---|
| Open pipeline | `open_pipeline_musd` | `[Open Pipeline]` |
| Weighted pipeline | `weighted_pipeline_musd` | `[Weighted Pipeline]` |
| Won revenue | `won_revenue_musd` | `[Won Revenue]` (remove all date filters) |
| Win rate | `win_rate` | `[Win Rate]` |
| Average won cycle | `avg_won_cycle_days` | `[Average Sales Cycle (Days)]` |
