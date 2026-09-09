# Power BI model

Connect Power BI to the Lakehouse (SQL analytics endpoint or the default semantic model) and use only the `dim_*` and `fact_*` tables.

## Relationships

| From (many) | To (one) | Note |
|---|---|---|
| `fact_opportunity[seller_id]` | `dim_seller[seller_id]` | |
| `fact_opportunity[account_id]` | `dim_account[account_id]` | |
| `fact_opportunity[stage]` | `dim_stage[stage]` | sort `stage` by `stage_order` |
| `fact_opportunity[created_date_key]` | `dim_date[date_key]` | active |
| `fact_opportunity[actual_close_date_key]` | `dim_date[date_key]` | inactive, used with USERELATIONSHIP |
| `fact_stage_history[opportunity_id]` | `fact_opportunity[opportunity_id]` | |
| `fact_stage_history[changed_date_key]` | `dim_date[date_key]` | |
| `fact_activity[seller_id]` | `dim_seller[seller_id]` | |
| `fact_activity[activity_date_key]` | `dim_date[date_key]` | |

Mark `dim_date` as the date table (`date` column).

## Measures

```dax
Open Pipeline = CALCULATE ( SUM ( fact_opportunity[amount] ), fact_opportunity[is_closed] = FALSE () )

Weighted Pipeline = CALCULATE ( SUM ( fact_opportunity[weighted_amount] ), fact_opportunity[is_closed] = FALSE () )

Open Deals = CALCULATE ( COUNTROWS ( fact_opportunity ), fact_opportunity[is_closed] = FALSE () )

Won Revenue = CALCULATE ( SUM ( fact_opportunity[amount] ), fact_opportunity[is_won] = TRUE () )

Deals Won = CALCULATE ( COUNTROWS ( fact_opportunity ), fact_opportunity[is_won] = TRUE () )

Deals Closed = CALCULATE ( COUNTROWS ( fact_opportunity ), fact_opportunity[is_closed] = TRUE () )

Win Rate = DIVIDE ( [Deals Won], [Deals Closed] )

Avg Deal Size (Won) = DIVIDE ( [Won Revenue], [Deals Won] )

Avg Days to Close = CALCULATE ( AVERAGE ( fact_opportunity[days_to_close] ), fact_opportunity[is_won] = TRUE () )

Won Revenue by Close Date =
    CALCULATE ( [Won Revenue], USERELATIONSHIP ( fact_opportunity[actual_close_date_key], dim_date[date_key] ) )

Quota = SUM ( dim_seller[quota_annual] )

Quota Attainment % = DIVIDE ( [Won Revenue by Close Date], [Quota] )

Avg Days in Stage = AVERAGE ( fact_stage_history[days_in_stage] )

Activities = COUNTROWS ( fact_activity )

Activities per Deal = DIVIDE ( [Activities], DISTINCTCOUNT ( fact_activity[opportunity_id] ) )
```

## Report pages

1. **Pipeline overview** - open pipeline, weighted pipeline, open deals, win rate; funnel by stage; pipeline by region and segment.
2. **Sales performance** - won revenue and quota attainment by seller / team; won revenue by fiscal quarter.
3. **Deal velocity** - average days to close, average days in each stage, activities per deal.

