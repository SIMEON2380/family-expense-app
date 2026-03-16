import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db
from family_budget.logic import get_yearly_history_tables


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Expense History", layout="wide")

DB["ensure_schema"]()

st.title("📜 Expense History")

df = DB["read_all_expenses"]()

if df.empty:
    st.info("No expenses added yet.")
else:
    year_tables = get_yearly_history_tables(df)

    for year, year_df in year_tables.items():
        st.subheader(f"{year}")

        household_total = float(year_df["amount"].sum()) if "amount" in year_df.columns else 0.0
        simeon_total = float(year_df["simeon_share"].sum()) if "simeon_share" in year_df.columns else 0.0
        bernice_total = float(year_df["bernice_share"].sum()) if "bernice_share" in year_df.columns else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total household bill", f"£{household_total:.2f}")
        col2.metric("Total payable by Simeon", f"£{simeon_total:.2f}")
        col3.metric("Total payable by Bernice", f"£{bernice_total:.2f}")

        display_df = year_df.copy()

        rename_map = {
            "expense_date": "Date",
            "bill_name": "Bill Name",
            "shop_name": "Shop Name",
            "amount": "Amount",
            "simeon_share": "Simeon Payable",
            "bernice_share": "Bernice Payable",
            "category": "Category",
            "expense_type": "Expense Type",
            "comments": "Comments",
        }

        display_df = display_df.rename(columns=rename_map)
        st.dataframe(display_df, use_container_width=True)

    st.subheader("Delete Expense")
    expense_ids = df["id"].tolist()
    selected_id = st.selectbox("Select expense ID to delete", expense_ids)

    if st.button("Delete Selected Expense"):
        DB["delete_expense"](int(selected_id))
        st.success("Expense deleted.")
        st.rerun()