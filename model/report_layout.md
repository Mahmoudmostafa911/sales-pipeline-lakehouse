# Report layout guide

Three pages, one story: *how healthy is the pipeline, who is converting it, and where do deals slow down?*
Build in Power BI Desktop on the Import model (or Direct Lake in Fabric) and save as `.pbip` next to this file.

Global slicers on every page: **Fiscal period**, **Region**, **Segment**, **Product family**.
Use a single accent colour for "Won", a neutral grey for "Lost" and a lighter tint for "Open" so the funnel and
outcome visuals read consistently.

---

## Page 1 — Pipeline Overview

| Zone | Visual | Fields / measures |
|---|---|---|
| KPI row | 5 cards | `[Open Pipeline]`, `[Weighted Pipeline]`, `[Won Revenue FYTD]`, `[Win Rate]`, `[Pipeline Coverage]` |
| Left | Funnel | `Stage[stage_name]` (open stages only) × `[Open Pipeline]`; tooltip `[Open Opportunities]`, `[Average Days Open]` |
| Centre | Clustered column + line | `Date[year_month]` × `[Won Revenue]` (columns) and `[Won Revenue Rolling 3M]` (line) |
| Right | Stacked bar | `Product[product_family]` × `[Open Pipeline]` by `Account[segment]` |
| Bottom | Matrix | `Seller[region]` › `Seller[team]` rows; `[Open Pipeline]`, `[Weighted Pipeline]`, `[Quota]`, `[Pipeline Coverage]` (conditional icon: ≥3x green, 2–3x amber, <2x red) |

## Page 2 — Seller Productivity

| Zone | Visual | Fields / measures |
|---|---|---|
| KPI row | 4 cards | `[Won Revenue]`, `[Won Deals]`, `[Won Revenue per Seller]`, `[Activities per Won Deal]` |
| Left | Table (ranked) | `Seller[seller_name]`, `Seller[region]`, `[Won Revenue]`, `[Quota Attainment %]` (data bar), `[Win Rate]`, `[Average Sales Cycle (Days)]` |
| Right top | Scatter | X `[Activities]`, Y `[Won Revenue]`, size `[Won Deals]`, legend `Seller[segment]`, detail `Seller[seller_name]` — shows effort vs outcome |
| Right bottom | 100 % stacked bar | `Seller[manager_name]` × `Activity[activity_type]` × `[Activities]` |
| Footer | Small multiples line | `[Win Rate]` by `Date[year_month]`, small multiples by `Seller[region]` |

## Page 3 — Sales Cycle & Conversion

| Zone | Visual | Fields / measures |
|---|---|---|
| KPI row | 3 cards | `[Average Sales Cycle (Days)]`, `[Win Rate]`, `[Lost Deals]` |
| Left | Funnel | `Stage[stage_name]` × `[Deals Reaching Stage]` — classic entry funnel |
| Centre | Clustered bar | `Stage[stage_name]` × `[Advance Rate %]` and `[Stage Conversion %]` |
| Right | Bar | `Stage[stage_name]` × `[Average Days in Stage]` — where deals stall |
| Bottom left | Box-and-whisker (custom visual) or histogram | `Opportunity[sales_cycle_days]` distribution by `Account[segment]` |
| Bottom right | Decomposition tree | `[Win Rate]` explained by `Opportunity[lead_source]`, `Account[industry]`, `Product[product]` |

## Optional Page 4 — Data Quality

Import `silver_dq_results` as `Data Quality` and show `[DQ Pass Rate %]`, a table of checks by run, and a line of
`[DQ Failed Rows]` over `run_ts`. This is a strong DP-700 talking point — data quality as a first-class output.

---

## Screenshots for the README

After the report is built, capture each page at 1280×720 and save as
`docs/img/page1_pipeline_overview.png`, `docs/img/page2_seller_productivity.png`,
`docs/img/page3_sales_cycle.png`, then replace the `<!-- TODO screenshot -->` markers in `README.md`.
