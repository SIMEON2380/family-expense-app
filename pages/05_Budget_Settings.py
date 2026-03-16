from datetime import date

import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Budget Settings", layout="wide")

DB["ensure_schema"]()

st.title("⚙️ Budget Settings")

today = date.today()

month_options = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

selected_month = st.selectbox("Month", month_options, index=today.month - 1)
selected_year = st.number_input("Year", min_value=2000, max_value=2100, value=today.year, step=1)

current_budget = DB["get_budget"](selected_month, int(selected_year))
default_value = current_budget if current_budget is not None else cfg.DEFAULT_MONTHLY_LIMIT

monthly_limit = st.number_input(
    "Monthly Limit",
    min_value=0.0,
    value=float(default_value),
    format="%.2f"
)

if st.button("Save Budget"):
    DB["save_budget"](selected_month, int(selected_year), float(monthly_limit))
    st.success("Budget saved successfully.")

st.info(f"Default monthly limit is £{cfg.DEFAULT_MONTHLY_LIMIT:.2f} until you change it.")