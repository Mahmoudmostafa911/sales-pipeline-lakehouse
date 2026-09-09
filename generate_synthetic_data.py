"""
Synthetic B2B sales-pipeline dataset generator
==============================================

Generates a fully fictional CRM-style dataset for the Sales Pipeline Lakehouse
project. Every seller, account and deal is invented; nothing here comes from a
real company.

The generator deliberately injects realistic data-quality problems so the
Silver layer has something to fix (see DATA_QUALITY_NOTES.md):

* exact duplicate rows and "stale" duplicates with an older last_modified_ts
* inconsistent casing / whitespace in stage names and currency codes
* null and negative amounts
* orphan opportunities that reference an account that does not exist
* mixed date formats in expected_close_date (ISO and dd/MM/yyyy)
* activities logged before the opportunity was created

Usage
-----
    python generate_synthetic_data.py --out raw

The run is deterministic (fixed seed), so re-running produces identical files.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------
# Reference data (all fictional)
# ----------------------------------------------------------------------------
SNAPSHOT_DATE = date(2025, 6, 30)          # "today" for the dataset
START_DATE = date(2023, 1, 1)

REGIONS = {
    "Americas": ["United States", "Canada", "Brazil", "Mexico"],
    "EMEA": ["Egypt", "United Arab Emirates", "Saudi Arabia", "Germany",
             "United Kingdom", "France", "Netherlands", "South Africa"],
    "APAC": ["India", "Singapore", "Australia", "Japan"],
}
REGION_WEIGHTS = {"Americas": 0.40, "EMEA": 0.40, "APAC": 0.20}
SEGMENTS = ["SMB", "Mid-Market"]
INDUSTRIES = ["Retail", "Manufacturing", "Healthcare", "Financial Services",
              "Education", "Logistics", "Professional Services", "Technology",
              "Hospitality", "Energy"]
PRODUCTS = {                       # product -> (base amount, family)
    "Cloud Suite": (18000, "Platform"),
    "Analytics Platform": (24000, "Data & AI"),
    "Security Bundle": (15000, "Security"),
    "Collaboration Tools": (9000, "Productivity"),
    "Support Plan": (6000, "Services"),
}
STAGES = ["Prospecting", "Qualification", "Proposal", "Negotiation"]
LEAD_SOURCES = ["Partner", "Inbound", "Outbound", "Event", "Referral"]
LEAD_SOURCE_WEIGHTS = [0.30, 0.25, 0.25, 0.10, 0.10]
ACTIVITY_TYPES = ["Call", "Email", "Meeting", "Demo"]
ACTIVITY_WEIGHTS = [0.35, 0.40, 0.15, 0.10]

FIRST_NAMES = ["Omar", "Sara", "Youssef", "Nour", "Ahmed", "Layla", "Karim", "Mona",
               "Hana", "Tarek", "Dina", "Ali", "Salma", "Hassan", "Farah", "Amir",
               "Liam", "Emma", "Noah", "Olivia", "Lucas", "Mia", "Ethan", "Sofia",
               "Arjun", "Priya", "Kenji", "Aiko", "Mateo", "Valentina", "Lucas", "Chloe",
               "Daniel", "Isabella", "Samuel", "Zara", "Adam", "Lina", "Rami", "Maya"]
LAST_NAMES = ["Hassan", "Ibrahim", "Saleh", "Mansour", "Khalil", "Farouk", "Nasser",
              "Smith", "Johnson", "Brown", "Garcia", "Martinez", "Müller", "Schmidt",
              "Dubois", "Rossi", "Patel", "Sharma", "Tanaka", "Sato", "Nguyen", "Kim",
              "Silva", "Costa", "Okafor", "Mensah", "Novak", "Larsen", "Fischer", "Walker"]
COMPANY_A = ["Blue", "North", "Delta", "Prime", "Silver", "Atlas", "Nova", "Summit",
             "Cedar", "Harbor", "Orbit", "Vertex", "Lumen", "Falcon", "Granite", "Pioneer",
             "Sahara", "Nile", "Coral", "Zenith"]
COMPANY_B = ["Logistics", "Retail", "Health", "Foods", "Industries", "Systems",
             "Consulting", "Energy", "Hotels", "Media", "Textiles", "Motors", "Pharma",
             "Learning", "Freight", "Capital", "Clinics", "Markets", "Studios", "Labs"]
COMPANY_SUFFIX = ["Ltd", "LLC", "GmbH", "S.A.", "Inc.", "Co.", "Group", "Holdings"]
MANAGERS = ["Yasmin El-Sayed", "Marcus Reed", "Ingrid Bauer", "Rohan Mehta",
            "Camila Duarte", "Kenta Mori"]


def _rand_date(start: date, end: date, size: int) -> np.ndarray:
    """Uniform random dates between start and end (inclusive)."""
    span = (end - start).days
    offsets = rng.integers(0, span + 1, size=size)
    return np.array([start + timedelta(days=int(o)) for o in offsets])


def _pick(values, size, p=None):
    return rng.choice(values, size=size, p=p)


# ----------------------------------------------------------------------------
# Sellers
# ----------------------------------------------------------------------------
def build_sellers(n: int = 40) -> pd.DataFrame:
    regions = _pick(list(REGION_WEIGHTS), n, p=list(REGION_WEIGHTS.values()))
    segments = _pick(SEGMENTS, n, p=[0.6, 0.4])
    names = set()
    full_names = []
    while len(full_names) < n:
        nm = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if nm not in names:
            names.add(nm)
            full_names.append(nm)
    quota = np.where(segments == "Mid-Market",
                     rng.integers(650, 950, n) * 1000,
                     rng.integers(380, 620, n) * 1000)
    df = pd.DataFrame({
        "seller_id": [f"S{str(i + 1).zfill(3)}" for i in range(n)],
        "seller_name": full_names,
        "region": regions,
        "segment": segments,
        "team": [f"{r} {s} Team" for r, s in zip(regions, segments)],
        "manager_name": _pick(MANAGERS, n),
        "hire_date": _rand_date(date(2018, 1, 1), date(2024, 9, 30), n),
        "quota_annual": quota,
        "is_active": _pick([True, False], n, p=[0.92, 0.08]),
    })
    return df


# ----------------------------------------------------------------------------
# Accounts
# ----------------------------------------------------------------------------
def build_accounts(sellers: pd.DataFrame, n: int = 500) -> pd.DataFrame:
    regions = _pick(list(REGION_WEIGHTS), n, p=list(REGION_WEIGHTS.values()))
    countries = [rng.choice(REGIONS[r]) for r in regions]
    segments = _pick(SEGMENTS, n, p=[0.6, 0.4])
    bands = np.where(segments == "SMB",
                     _pick(["10-49", "50-249"], n, p=[0.55, 0.45]),
                     _pick(["250-999", "1000-4999"], n, p=[0.7, 0.3]))
    used = set()
    names = []
    while len(names) < n:
        nm = f"{rng.choice(COMPANY_A)} {rng.choice(COMPANY_B)} {rng.choice(COMPANY_SUFFIX)}"
        if nm in used:
            nm = f"{nm} {len(names)}"
        used.add(nm)
        names.append(nm)

    # owner = a seller from the same region & segment when one exists
    owners = []
    for r, s in zip(regions, segments):
        pool = sellers[(sellers.region == r) & (sellers.segment == s)]
        if pool.empty:
            pool = sellers[sellers.region == r]
        owners.append(rng.choice(pool.seller_id.values))

    return pd.DataFrame({
        "account_id": [f"A{str(i + 1).zfill(4)}" for i in range(n)],
        "account_name": names,
        "industry": _pick(INDUSTRIES, n),
        "country": countries,
        "region": regions,
        "segment": segments,
        "employee_band": bands,
        "created_date": _rand_date(date(2021, 1, 1), date(2025, 3, 31), n),
        "owner_seller_id": owners,
    })


# ----------------------------------------------------------------------------
# Opportunities + stage history + activities
# ----------------------------------------------------------------------------
def build_opportunities(sellers: pd.DataFrame, accounts: pd.DataFrame, n: int = 3000):
    acct_idx = rng.integers(0, len(accounts), n)
    acct = accounts.iloc[acct_idx].reset_index(drop=True)

    # 90 % owned by the account owner, 10 % by another seller in the region
    seller_ids = acct.owner_seller_id.values.copy()
    reassign = rng.random(n) < 0.10
    for i in np.where(reassign)[0]:
        pool = sellers[sellers.region == acct.region.iloc[i]].seller_id.values
        seller_ids[i] = rng.choice(pool)

    products = _pick(list(PRODUCTS), n, p=[0.28, 0.22, 0.20, 0.18, 0.12])
    base = np.array([PRODUCTS[p][0] for p in products], dtype=float)
    seg_mult = np.where(acct.segment.values == "Mid-Market", 1.8, 1.0)
    amount = base * seg_mult * rng.lognormal(mean=0.0, sigma=0.45, size=n)
    amount = (np.round(amount / 100) * 100).astype(float)

    # 65 % of deals spread over the full history, 35 % created in the last ~5 months,
    # so the snapshot contains a healthy open pipeline as well as closed history
    n_recent = int(n * 0.35)
    created = np.concatenate([
        _rand_date(START_DATE, SNAPSHOT_DATE - timedelta(days=150), n - n_recent),
        _rand_date(SNAPSHOT_DATE - timedelta(days=150), SNAPSHOT_DATE - timedelta(days=3), n_recent),
    ])
    rng.shuffle(created)
    age_days = np.array([(SNAPSHOT_DATE - c).days for c in created])
    lead_source = _pick(LEAD_SOURCES, n, p=LEAD_SOURCE_WEIGHTS)

    # planned cycle used for the expected close date
    planned_cycle = rng.integers(45, 130, n)
    expected_close = np.array([c + timedelta(days=int(d)) for c, d in zip(created, planned_cycle)])

    # actual outcome ------------------------------------------------------
    # Mid-Market deals take ~1.6x longer than SMB deals
    cycle_scale = np.where(acct.segment.values == "Mid-Market", 1.6, 1.0)
    cycle_won = np.clip(rng.gamma(shape=4.0, scale=15.0, size=n) * cycle_scale, 10, 320).astype(int)   # SMB mean ~60
    cycle_lost = np.clip(rng.gamma(shape=3.0, scale=15.0, size=n) * cycle_scale, 7, 280).astype(int)   # SMB mean ~45

    # win probability varies by lead source and segment
    p_win = np.full(n, 0.32)
    p_win += np.where(lead_source == "Referral", 0.12, 0)
    p_win += np.where(lead_source == "Partner", 0.05, 0)
    p_win -= np.where(lead_source == "Outbound", 0.06, 0)
    p_win += np.where(acct.segment.values == "SMB", 0.03, -0.03)
    is_won_draw = rng.random(n) < p_win

    actual_cycle = np.where(is_won_draw, cycle_won, cycle_lost)
    closed = actual_cycle <= age_days           # deal had time to close
    is_won = closed & is_won_draw
    is_lost = closed & ~is_won_draw

    stage = np.empty(n, dtype=object)
    stage[is_won] = "Closed Won"
    stage[is_lost] = "Closed Lost"
    # open deals: progress through the funnel according to age / planned cycle
    open_idx = np.where(~closed)[0]
    for i in open_idx:
        progress = min(age_days[i] / planned_cycle[i], 0.99)
        if progress < 0.25:
            stage[i] = "Prospecting"
        elif progress < 0.5:
            stage[i] = "Qualification"
        elif progress < 0.75:
            stage[i] = "Proposal"
        else:
            stage[i] = "Negotiation"

    probability_map = {"Prospecting": 0.10, "Qualification": 0.25, "Proposal": 0.50,
                       "Negotiation": 0.75, "Closed Won": 1.00, "Closed Lost": 0.00}
    probability = np.array([probability_map[s] for s in stage])

    actual_close = np.array([
        (c + timedelta(days=int(d))) if cl else None
        for c, d, cl in zip(created, actual_cycle, closed)
    ], dtype=object)

    last_modified = np.array([
        datetime.combine(ac if ac is not None else SNAPSHOT_DATE - timedelta(days=int(rng.integers(0, 7))),
                         datetime.min.time()) + timedelta(hours=int(rng.integers(8, 19)), minutes=int(rng.integers(0, 60)))
        for ac in actual_close
    ])

    opps = pd.DataFrame({
        "opportunity_id": [f"O{str(i + 1).zfill(6)}" for i in range(n)],
        "opportunity_name": [f"{a} - {p}" for a, p in zip(acct.account_name.values, products)],
        "account_id": acct.account_id.values,
        "seller_id": seller_ids,
        "product": products,
        "lead_source": lead_source,
        "stage": stage,
        "probability": probability,
        "amount": amount,
        "currency": "USD",
        "created_date": created,
        "expected_close_date": expected_close,
        "actual_close_date": actual_close,
        "last_modified_ts": last_modified,
    })

    # ---- stage history ----------------------------------------------------
    hist_rows = []
    final_stage_index = {s: i for i, s in enumerate(STAGES)}
    for row in opps.itertuples(index=False):
        if row.stage in ("Closed Won", "Closed Lost"):
            end_dt = row.actual_close_date
            # lost deals may exit from any intermediate stage; won deals pass through all
            depth = len(STAGES) if row.stage == "Closed Won" else int(rng.integers(1, len(STAGES) + 1))
        else:
            end_dt = SNAPSHOT_DATE
            depth = final_stage_index[row.stage] + 1
        total_days = max((end_dt - row.created_date).days, 1)
        # random cut points inside the cycle
        cuts = np.sort(rng.random(depth - 1)) * total_days if depth > 1 else np.array([])
        ts_prev = datetime.combine(row.created_date, datetime.min.time()) + timedelta(hours=9)
        hist_rows.append((row.opportunity_id, None, "Prospecting", ts_prev, row.seller_id))
        for k in range(1, depth):
            ts = datetime.combine(row.created_date + timedelta(days=int(cuts[k - 1])),
                                  datetime.min.time()) + timedelta(hours=int(rng.integers(8, 18)))
            hist_rows.append((row.opportunity_id, STAGES[k - 1], STAGES[k], ts, row.seller_id))
        if row.stage in ("Closed Won", "Closed Lost"):
            ts = datetime.combine(end_dt, datetime.min.time()) + timedelta(hours=int(rng.integers(9, 18)))
            hist_rows.append((row.opportunity_id, STAGES[depth - 1], row.stage, ts, row.seller_id))

    history = pd.DataFrame(hist_rows, columns=["opportunity_id", "from_stage", "to_stage",
                                               "changed_at", "changed_by_seller_id"])
    history.insert(0, "history_id", [f"H{str(i + 1).zfill(7)}" for i in range(len(history))])

    # ---- activities -------------------------------------------------------
    act_rows = []
    for row in opps.itertuples(index=False):
        depth = 4 if row.stage in ("Closed Won", "Closed Lost") else final_stage_index[row.stage] + 1
        n_act = int(rng.poisson(1.5 + 1.2 * depth))
        end_dt = row.actual_close_date if row.actual_close_date is not None else SNAPSHOT_DATE
        span = max((end_dt - row.created_date).days, 1)
        for _ in range(n_act):
            a_type = rng.choice(ACTIVITY_TYPES, p=ACTIVITY_WEIGHTS)
            ts = datetime.combine(row.created_date + timedelta(days=int(rng.integers(0, span + 1))),
                                  datetime.min.time()) + timedelta(hours=int(rng.integers(8, 19)),
                                                                   minutes=int(rng.integers(0, 60)))
            duration = {"Call": rng.integers(5, 45), "Email": 0,
                        "Meeting": rng.integers(30, 90), "Demo": rng.integers(45, 120)}[a_type]
            act_rows.append((row.opportunity_id, row.seller_id, a_type, ts, int(duration)))
    activities = pd.DataFrame(act_rows, columns=["opportunity_id", "seller_id", "activity_type",
                                                 "activity_ts", "duration_minutes"])
    activities.insert(0, "activity_id", [f"ACT{str(i + 1).zfill(7)}" for i in range(len(activities))])
    return opps, history, activities


# ----------------------------------------------------------------------------
# Deliberate data-quality problems (documented in DATA_QUALITY_NOTES.md)
# ----------------------------------------------------------------------------
def inject_quality_issues(opps: pd.DataFrame, activities: pd.DataFrame):
    opps = opps.copy()
    n = len(opps)

    # 1) inconsistent casing / whitespace in stage (~3 %)
    idx = rng.choice(n, size=int(n * 0.03), replace=False)
    variants = [lambda s: s.lower(), lambda s: s.upper(), lambda s: f" {s} ", lambda s: s.replace(" ", "  ")]
    opps.loc[idx, "stage"] = [variants[int(rng.integers(0, len(variants)))](s) for s in opps.loc[idx, "stage"]]

    # 2) currency in lower case (~2 %)
    idx = rng.choice(n, size=int(n * 0.02), replace=False)
    opps.loc[idx, "currency"] = "usd"

    # 3) null amounts on open deals (~1.5 %)
    open_mask = ~opps.stage.str.strip().str.lower().isin(["closed won", "closed lost"])
    open_idx = np.where(open_mask.values)[0]
    idx = rng.choice(open_idx, size=int(n * 0.015), replace=False)
    opps.loc[idx, "amount"] = np.nan

    # 4) negative amounts (~0.3 %) - data entry errors
    idx = rng.choice(n, size=max(int(n * 0.003), 5), replace=False)
    opps.loc[idx, "amount"] = -opps.loc[idx, "amount"].abs()

    # 5) orphan account references (~0.5 %)
    idx = rng.choice(n, size=max(int(n * 0.005), 10), replace=False)
    opps.loc[idx, "account_id"] = [f"A{str(9900 + k).zfill(4)}" for k in range(len(idx))]

    # 6) mixed date format in expected_close_date (~2 %): dd/MM/yyyy instead of ISO
    opps["expected_close_date"] = opps["expected_close_date"].apply(lambda d: d.isoformat())
    idx = rng.choice(n, size=int(n * 0.02), replace=False)
    opps.loc[idx, "expected_close_date"] = [
        datetime.strptime(v, "%Y-%m-%d").strftime("%d/%m/%Y") for v in opps.loc[idx, "expected_close_date"]
    ]

    # 7) exact duplicate rows (~1 %)
    dup_exact = opps.sample(n=int(n * 0.01), random_state=SEED)

    # 8) stale duplicates: same opportunity_id, older last_modified_ts and an earlier stage (~0.5 %)
    stale = opps.sample(n=int(n * 0.005), random_state=SEED + 1).copy()
    stale["last_modified_ts"] = stale["last_modified_ts"] - pd.to_timedelta(rng.integers(3, 40, len(stale)), unit="D")
    stale["stage"] = "Qualification"
    stale["probability"] = 0.25

    opps = pd.concat([opps, dup_exact, stale], ignore_index=True)
    opps = opps.sample(frac=1.0, random_state=SEED).reset_index(drop=True)   # shuffle

    # 9) activities dated before the opportunity existed (~0.5 %)
    activities = activities.copy()
    idx = rng.choice(len(activities), size=int(len(activities) * 0.005), replace=False)
    activities.loc[idx, "activity_ts"] = activities.loc[idx, "activity_ts"] - pd.to_timedelta(
        rng.integers(400, 900, len(idx)), unit="D")
    return opps, activities


# ----------------------------------------------------------------------------
def main(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    sellers = build_sellers()
    accounts = build_accounts(sellers)
    opps, history, activities = build_opportunities(sellers, accounts)
    opps, activities = inject_quality_issues(opps, activities)

    sellers.to_csv(os.path.join(out_dir, "sellers.csv"), index=False)
    accounts.to_csv(os.path.join(out_dir, "accounts.csv"), index=False)
    opps.to_csv(os.path.join(out_dir, "opportunities.csv"), index=False,
                date_format="%Y-%m-%d %H:%M:%S")
    history.to_csv(os.path.join(out_dir, "opportunity_stage_history.csv"), index=False,
                   date_format="%Y-%m-%d %H:%M:%S")
    activities.to_csv(os.path.join(out_dir, "activities.csv"), index=False,
                      date_format="%Y-%m-%d %H:%M:%S")

    print(f"sellers                    {len(sellers):>7,}")
    print(f"accounts                   {len(accounts):>7,}")
    print(f"opportunities (with dups)  {len(opps):>7,}")
    print(f"opportunity_stage_history  {len(history):>7,}")
    print(f"activities                 {len(activities):>7,}")
    print(f"written to {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="raw", help="output folder for the CSV files (default: raw)")
    main(parser.parse_args().out)
