from datetime import date

import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Add Expense", layout="wide")

DB["ensure_schema"]()

st.title("➕ Add Food Expense")

st.caption("This page is now only for manual food spending.")

with st.form("add_expense_form"):
    expense_date = st.date_input("Expense Date", value=date.today())
    bill_name = st.text_input("Bill Name")
    shop_name = st.text_input("Shop Name")
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    comments = st.text_area("Comments")

    submitted = st.form_submit_button("Save Expense")

if submitted:
    if not bill_name.strip():
        st.error("Bill Name is required.")
    else:
        DB["add_expense"](
            str(expense_date),
            bill_name.strip().upper(),
            shop_name.strip().upper(),
            float(amount),
            0.0,
            0.0,
            comments.strip(),
            "Food",
            "Variable",
        )
        st.success("Food expense saved successfully.")