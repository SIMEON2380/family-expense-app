import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db
from family_budget.logic import parse_budget_excel


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Import Excel", layout="wide")

DB["ensure_schema"]()

st.title("📥 Import Excel Budget")

st.write("Upload your budget workbook to import historical data into the app.")

uploaded_file = st.file_uploader("Choose Excel file", type=["xlsx"])

if uploaded_file is not None:
    parsed_df = parse_budget_excel(uploaded_file)

    if parsed_df.empty:
        st.warning("No valid budget rows were found in this workbook.")
    else:
        st.success(f"Found {len(parsed_df)} rows ready to import.")
        st.dataframe(parsed_df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Import into Database"):
                inserted = DB["bulk_insert_expenses"](parsed_df)
                st.success(f"Imported {inserted} rows successfully.")

        with col2:
            if st.button("Clear All Existing Expenses First, Then Import"):
                DB["clear_all_expenses"]()
                inserted = DB["bulk_insert_expenses"](parsed_df)
                st.success(f"Cleared existing data and imported {inserted} rows successfully.")