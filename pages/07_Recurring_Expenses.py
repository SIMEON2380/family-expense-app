from datetime import date

import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Recurring Expenses", layout="wide")

DB["ensure_schema"]()

st.title("🔁 Recurring Expenses")

st.subheader("Add Recurring Expense")

with st.form("add_recurring_expense_form"):
    bill_name = st.text_input("Bill Name")
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    simeon_share = st.number_input("Simeon Share", min_value=0.0, format="%.2f")
    bernice_share = st.number_input("Bernice Share", min_value=0.0, format="%.2f")
    category = st.selectbox("Category", cfg.CATEGORIES)
    expense_type = st.selectbox("Expense Type", cfg.EXPENSE_TYPES, index=0)
    comments = st.text_area("Comments")
    frequency = st.selectbox("Frequency", ["Monthly"])
    day_of_month = st.number_input("Day of Month", min_value=1, max_value=28, value=1, step=1)

    submitted = st.form_submit_button("Save Recurring Expense")

if submitted:
    if not bill_name.strip():
        st.error("Bill Name is required.")
    else:
        DB["add_recurring_expense"](
            bill_name=bill_name.strip(),
            amount=float(amount),
            simeon_share=float(simeon_share),
            bernice_share=float(bernice_share),
            comments=comments.strip(),
            category=category,
            expense_type=expense_type,
            frequency=frequency,
            day_of_month=int(day_of_month),
            is_active=1,
        )
        st.success("Recurring expense saved successfully.")
        st.rerun()

st.subheader("Generate This Month's Recurring Expenses")

today = date.today()
col1, col2 = st.columns(2)

with col1:
    gen_year = st.number_input("Year", min_value=2000, max_value=2100, value=today.year, step=1)

with col2:
    gen_month = st.number_input("Month", min_value=1, max_value=12, value=today.month, step=1)

if st.button("Generate Recurring Expenses for Selected Month"):
    result = DB["generate_recurring_for_month"](int(gen_year), int(gen_month))
    st.success(
        f"Generation complete. Inserted: {result['inserted']} | Skipped duplicates: {result['skipped']}"
    )

st.subheader("Saved Recurring Expenses")

recurring_df = DB["read_all_recurring_expenses"]()

if recurring_df.empty:
    st.info("No recurring expenses added yet.")
else:
    st.dataframe(recurring_df, use_container_width=True)

    recurring_ids = recurring_df["id"].tolist()
    selected_id = st.selectbox("Select recurring expense ID to delete", recurring_ids)

    if st.button("Delete Selected Recurring Expense"):
        DB["delete_recurring_expense"](int(selected_id))
        st.success("Recurring expense deleted.")
        st.rerun()