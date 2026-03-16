from datetime import date

import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db
from family_budget.logic import get_monthly_totals, get_yearly_total


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Dashboard", layout="wide")

DB["ensure_schema"]()

st.title("📊 Dashboard")

df = DB["read_all_expenses"]()

today = date.today()
selected_year = st.selectbox("Select year", options=list(range(today.year - 5, today.year + 1)), index=5)
selected_month = st.selectbox(
    "Select month",
    options=[
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ],
    index=today.month - 1
)

totals = get_monthly_totals(df, selected_year, selected_month)
year_total = get_yearly_total(df, selected_year)
budget = DB["get_budget"](selected_month, selected_year)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total this month", f"£{totals['total']:.2f}")
col2.metric("Fixed this month", f"£{totals['fixed']:.2f}")
col3.metric("Variable this month", f"£{totals['variable']:.2f}")
col4.metric("Food this month", f"£{totals['food']:.2f}")

st.metric("Year total", f"£{year_total:.2f}")

if budget is not None:
    remaining = budget - totals["total"]
    percent_used = (totals["total"] / budget * 100) if budget > 0 else 0

    st.subheader("Monthly Budget")
    st.write(f"Budget for {selected_month} {selected_year}: **£{budget:.2f}**")
    st.write(f"Remaining: **£{remaining:.2f}**")
    st.progress(min(int(percent_used), 100))

    if percent_used >= 100:
        st.error("You have reached or exceeded your monthly budget.")
    elif percent_used >= 80:
        st.warning("You are getting close to your monthly budget.")
    else:
        st.success("You are within your monthly budget.")
else:
    st.info("No monthly budget has been set yet.")