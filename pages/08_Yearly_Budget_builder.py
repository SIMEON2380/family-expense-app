import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db
from family_budget.logic import build_yearly_budget_from_source


cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title=f"{cfg.APP_TITLE} - Yearly Budget Builder", layout="wide")

DB["ensure_schema"]()

st.title("🧱 Yearly Budget Builder")
st.write("Build a new year's budget from an existing year, with optional increase and automatic 50/50 split.")

existing_years = DB["get_existing_years"]()

if not existing_years:
    st.info("No source years found yet. Import or add some data first.")
else:
    source_year = st.selectbox("Source Year", options=existing_years, index=len(existing_years) - 1)
    target_year = st.number_input("Target Year", min_value=2000, max_value=2100, value=int(source_year) + 1, step=1)
    increase_pct = st.number_input("Apply % increase to all amounts", value=0.0, step=1.0, format="%.2f")

    if st.button("Load Source Year Budget"):
        source_df = DB["read_expenses_by_year"](int(source_year))

        if source_df.empty:
            st.error("No data found for the selected source year.")
        else:
            preview_df = build_yearly_budget_from_source(source_df, int(target_year), float(increase_pct))
            st.session_state["yearly_budget_preview"] = preview_df
            st.session_state["yearly_budget_target_year"] = int(target_year)

    if "yearly_budget_preview" in st.session_state:
        preview_df = st.session_state["yearly_budget_preview"].copy()
        preview_target_year = st.session_state.get("yearly_budget_target_year", int(target_year))

        st.subheader(f"Preview for {preview_target_year}")

        edited_df = st.data_editor(
            preview_df,
            use_container_width=True,
            num_rows="dynamic",
            key="yearly_budget_editor",
            hide_index=True,
        )

        if not edited_df.empty:
            edited_df["bill_name"] = edited_df["bill_name"].fillna("").astype(str).str.upper()
            edited_df["shop_name"] = edited_df["shop_name"].fillna("").astype(str).str.upper()
            edited_df["amount"] = edited_df["amount"].fillna(0).astype(float).round(2)

            edited_df["simeon_share"] = (edited_df["amount"] / 2).round(2)
            edited_df["bernice_share"] = (edited_df["amount"] - edited_df["simeon_share"]).round(2)
            edited_df["expense_date"] = f"{preview_target_year}-01-01"

        total_amount = float(edited_df["amount"].sum()) if not edited_df.empty else 0.0
        total_simeon = float(edited_df["simeon_share"].sum()) if not edited_df.empty else 0.0
        total_bernice = float(edited_df["bernice_share"].sum()) if not edited_df.empty else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Household Budget", f"£{total_amount:.2f}")
        c2.metric("Simeon Total", f"£{total_simeon:.2f}")
        c3.metric("Bernice Total", f"£{total_bernice:.2f}")

        target_exists = DB["year_exists"](int(preview_target_year))
        if target_exists:
            st.warning(f"Year {preview_target_year} already exists in the database. Saving can replace it.")

        replace_existing = st.checkbox(
            f"Replace existing data for {preview_target_year} before saving",
            value=bool(target_exists),
        )

        if st.button("Save New Year Budget"):
            if edited_df.empty:
                st.error("There is no data to save.")
            else:
                save_df = edited_df.copy()

                required_columns = [
                    "expense_date",
                    "bill_name",
                    "shop_name",
                    "amount",
                    "simeon_share",
                    "bernice_share",
                    "comments",
                    "category",
                    "expense_type",
                ]

                for col in required_columns:
                    if col not in save_df.columns:
                        if col in ["amount", "simeon_share", "bernice_share"]:
                            save_df[col] = 0.0
                        else:
                            save_df[col] = ""

                save_df = save_df[required_columns].copy()

                if replace_existing:
                    DB["delete_expenses_by_year"](int(preview_target_year))

                inserted = DB["bulk_insert_expenses"](save_df)
                st.success(f"Saved {inserted} rows for year {preview_target_year}.")