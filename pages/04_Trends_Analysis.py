import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db
from family_budget.logic import (
    get_bill_growth_summary,
    get_food_trend,
    get_monthly_trend,
    get_shop_spend,
    get_top_growth_insights,
    get_year_on_year_summary,
)


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Trends Analysis", layout="wide")

DB["ensure_schema"]()

st.title("📈 Trends Analysis")

df = DB["read_all_expenses"]()

if df.empty:
    st.info("No expense data available yet.")
else:
    yoy = get_year_on_year_summary(df)
    monthly = get_monthly_trend(df)
    food = get_food_trend(df)
    growth = get_bill_growth_summary(df)
    shops = get_shop_spend(df)
    insights = get_top_growth_insights(df)

    if not yoy.empty:
        latest_total = float(yoy.iloc[-1]["total"])
        first_total = float(yoy.iloc[0]["total"])
        overall_growth = None if first_total == 0 else ((latest_total - first_total) / first_total) * 100

        highest_year_row = yoy.sort_values("total", ascending=False).iloc[0]
        lowest_year_row = yoy.sort_values("total", ascending=True).iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Latest yearly total", f"£{latest_total:.2f}")
        c2.metric("Highest year", f"{int(highest_year_row['year'])}", f"£{highest_year_row['total']:.2f}")
        c3.metric("Lowest year", f"{int(lowest_year_row['year'])}", f"£{lowest_year_row['total']:.2f}")
        c4.metric("Overall growth", f"{overall_growth:.2f}%" if overall_growth is not None else "N/A")

    st.subheader("Plain-English Growth Insights")
    if insights:
        for item in insights:
            st.write(f"• {item}")
    else:
        st.info("Not enough multi-year data yet for bill-level growth insights.")

    st.subheader("Year-on-Year Household Totals")
    st.dataframe(yoy, use_container_width=True)

    if not monthly.empty:
        st.subheader("Monthly Expense Trend")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(monthly["year_month"], monthly["amount"])
        ax.set_xlabel("Month")
        ax.set_ylabel("Amount (£)")
        ax.tick_params(axis="x", rotation=45)
        st.pyplot(fig)

    if not food.empty:
        st.subheader("Food Spending Trend")
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(food["year_month"], food["amount"])
        ax2.set_xlabel("Month")
        ax2.set_ylabel("Food Amount (£)")
        ax2.tick_params(axis="x", rotation=45)
        st.pyplot(fig2)

    if not shops.empty:
        st.subheader("Spend by Shop")
        st.dataframe(shops, use_container_width=True)

        top_shop = shops.iloc[0]
        st.success(f"Top shop right now: {top_shop['shop_name']} at £{top_shop['amount']:.2f}")

        fig3, ax3 = plt.subplots(figsize=(10, 4))
        top_shops = shops.head(10)
        ax3.bar(top_shops["shop_name"], top_shops["amount"])
        ax3.set_xlabel("Shop")
        ax3.set_ylabel("Amount (£)")
        ax3.tick_params(axis="x", rotation=45)
        st.pyplot(fig3)
    else:
        st.info("No shop-name data recorded yet.")

    st.subheader("Bill Growth Comparison")
    if not growth.empty:
        growth_display = growth.copy()
        growth_display = growth_display.rename(
            columns={
                "bill_name": "Bill Name",
                "first_year": "First Year",
                "latest_year": "Latest Year",
                "first_amount": "First Amount",
                "latest_amount": "Latest Amount",
                "change_amount": "Change Amount",
                "growth_pct": "Growth %",
            }
        )
        st.dataframe(growth_display, use_container_width=True)

        lively_examples = growth.dropna(subset=["growth_pct"]).head(5)
        if not lively_examples.empty:
            st.subheader("Quick Story View")
            for _, row in lively_examples.iterrows():
                st.write(
                    f"**{row['bill_name']}** was **£{row['first_amount']:.2f}** in **{int(row['first_year'])}** "
                    f"and is now **£{row['latest_amount']:.2f}** in **{int(row['latest_year'])}** "
                    f"— growth of **{row['growth_pct']:.2f}%**."
                )
    else:
        st.info("Not enough bill history yet for growth comparison.")