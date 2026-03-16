import streamlit as st
import pandas as pd

from family_budget.config import Config
from family_budget.db import make_db
from family_budget.logic import prepare_expense_dataframe


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Expense Intelligence", layout="wide")

DB["ensure_schema"]()

st.title("🧠 Expense Intelligence")

df = DB["read_all_expenses"]()

if df.empty:
    st.info("No data available yet.")
    st.stop()

df = prepare_expense_dataframe(df)

# Make sure expected columns exist
required_defaults = {
    "bill_name": "",
    "shop_name": "",
    "amount": 0.0,
    "category": "",
    "simeon_share": 0.0,
    "bernice_share": 0.0,
}

for col, default_value in required_defaults.items():
    if col not in df.columns:
        df[col] = default_value

df["bill_name"] = df["bill_name"].fillna("").astype(str).str.strip()
df["shop_name"] = df["shop_name"].fillna("").astype(str).str.strip()
df["category"] = df["category"].fillna("").astype(str).str.strip()
df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
df["simeon_share"] = pd.to_numeric(df["simeon_share"], errors="coerce").fillna(0.0)
df["bernice_share"] = pd.to_numeric(df["bernice_share"], errors="coerce").fillna(0.0)

# Remove rows with invalid dates
df = df[df["expense_date"].notna()].copy()

if df.empty:
    st.warning("All records have invalid dates, so there is nothing to analyse.")
    st.stop()

df["year_month"] = df["expense_date"].dt.strftime("%Y-%m")

# -------------------------
# YEAR ANALYSIS
# -------------------------
st.subheader("Year Overview")

year_summary = df.groupby("year", as_index=False)["amount"].sum()

if not year_summary.empty:
    highest_year = year_summary.sort_values("amount", ascending=False).iloc[0]
    lowest_year = year_summary.sort_values("amount", ascending=True).iloc[0]

    col1, col2 = st.columns(2)

    col1.metric(
        "Highest spending year",
        f"{int(highest_year['year'])}",
        f"£{highest_year['amount']:.2f}"
    )

    col2.metric(
        "Lowest spending year",
        f"{int(lowest_year['year'])}",
        f"£{lowest_year['amount']:.2f}"
    )

    st.dataframe(year_summary, use_container_width=True)
else:
    st.info("No yearly summary available.")

st.divider()

# -------------------------
# MONTH ANALYSIS
# -------------------------
st.subheader("Month Overview")

month_summary = df.groupby("year_month", as_index=False)["amount"].sum()

if not month_summary.empty:
    highest_month = month_summary.sort_values("amount", ascending=False).iloc[0]

    st.metric(
        "Highest spending month ever",
        highest_month["year_month"],
        f"£{highest_month['amount']:.2f}"
    )

    st.dataframe(month_summary, use_container_width=True)
else:
    st.info("No monthly summary available.")

st.divider()

# -------------------------
# FOOD ANALYSIS
# -------------------------
st.subheader("Food Insights")

food_df = df[df["category"].str.upper() == "FOOD"].copy()

if not food_df.empty:
    monthly_food = food_df.groupby("year_month", as_index=False)["amount"].sum()

    if not monthly_food.empty:
        avg_food = monthly_food["amount"].mean()
        highest_food_month = monthly_food.sort_values("amount", ascending=False).iloc[0]

        c1, c2 = st.columns(2)
        c1.metric("Average monthly food spending", f"£{avg_food:.2f}")
        c2.metric(
            "Highest food month",
            highest_food_month["year_month"],
            f"£{highest_food_month['amount']:.2f}"
        )

        st.dataframe(monthly_food, use_container_width=True)
    else:
        st.info("No monthly food summary available.")
else:
    st.info("No food data found yet.")

st.divider()

# -------------------------
# SHOP ANALYSIS
# -------------------------
st.subheader("Shop Insights")

shop_df = df[df["shop_name"] != ""].copy()

if not shop_df.empty:
    shop_totals = (
        shop_df.groupby("shop_name", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )

    if not shop_totals.empty:
        top_shop = shop_totals.iloc[0]
        cheapest_shop = shop_totals.iloc[-1]

        col1, col2 = st.columns(2)

        col1.metric(
            "Most expensive shop",
            top_shop["shop_name"],
            f"£{top_shop['amount']:.2f}"
        )

        col2.metric(
            "Least expensive shop",
            cheapest_shop["shop_name"],
            f"£{cheapest_shop['amount']:.2f}"
        )

        st.dataframe(shop_totals, use_container_width=True)
    else:
        st.info("No shop totals available.")
else:
    st.info("No shop-name data recorded yet.")

st.divider()

# -------------------------
# BILL GROWTH
# -------------------------
st.subheader("Bill Growth")

bill_growth_source = (
    df[df["bill_name"] != ""]
    .groupby(["year", "bill_name"], as_index=False)["amount"]
    .sum()
)

growth_rows = []

for bill, group in bill_growth_source.groupby("bill_name"):
    group = group.sort_values("year")

    if len(group) < 2:
        continue

    first = group.iloc[0]
    last = group.iloc[-1]

    first_amount = float(first["amount"])
    last_amount = float(last["amount"])

    if first_amount == 0:
        continue

    growth_pct = ((last_amount - first_amount) / first_amount) * 100

    growth_rows.append(
        {
            "Bill Name": bill,
            "Start Year": int(first["year"]),
            "End Year": int(last["year"]),
            "Start Amount": round(first_amount, 2),
            "End Amount": round(last_amount, 2),
            "Growth %": round(growth_pct, 2),
        }
    )

growth_df = pd.DataFrame(growth_rows)

if not growth_df.empty:
    growth_df = growth_df.sort_values("Growth %", ascending=False)

    biggest_growth = growth_df.iloc[0]

    st.success(
        f"{biggest_growth['Bill Name']} moved from £{biggest_growth['Start Amount']:.2f} "
        f"in {int(biggest_growth['Start Year'])} to £{biggest_growth['End Amount']:.2f} "
        f"in {int(biggest_growth['End Year'])} — growth of {biggest_growth['Growth %']:.2f}%."
    )

    st.dataframe(growth_df, use_container_width=True)
else:
    st.info("Not enough multi-year bill data yet for growth analysis.")