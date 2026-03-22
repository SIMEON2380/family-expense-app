import sqlite3
import streamlit as st
import pandas as pd

from family_budget.config import Config
from family_budget.db import make_db

cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title="Yearly Budget View", layout="wide")
st.title("📅 Yearly Budget View")

DB["ensure_schema"]()

con = sqlite3.connect(DB["db_path"])
con.row_factory = sqlite3.Row

# ---- Load available years ----
years_df = pd.read_sql_query(
    "SELECT year FROM budget_years ORDER BY year DESC",
    con,
)

if years_df.empty:
    st.warning("No budget years found yet.")
    st.stop()

selected_year = st.selectbox("Select Year", years_df["year"].tolist())

# ---- Category budget view ----
budget_df = pd.read_sql_query(
    """
    SELECT
        c.name AS category,
        b.original_amount,
        b.current_amount,
        (b.current_amount - b.original_amount) AS change_amount
    FROM budget_lines b
    JOIN budget_categories c
        ON b.category_id = c.id
    JOIN budget_years y
        ON b.budget_year_id = y.id
    WHERE y.year = ?
    ORDER BY c.name ASC
    """,
    con,
    params=(selected_year,),
)

if budget_df.empty:
    st.info("No budget has been set for this year yet.")
    st.stop()

# ---- Summary figures ----
original_total = float(budget_df["original_amount"].sum())
current_total = float(budget_df["current_amount"].sum())
change_total = float(budget_df["change_amount"].sum())

changes_df = pd.read_sql_query(
    """
    SELECT COUNT(*) AS change_count
    FROM budget_adjustments a
    JOIN budget_lines b
        ON a.budget_line_id = b.id
    JOIN budget_years y
        ON b.budget_year_id = y.id
    WHERE y.year = ?
    """,
    con,
    params=(selected_year,),
)

change_count = int(changes_df.iloc[0]["change_count"])
category_count = int(len(budget_df))

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Original Total", f"£{original_total:,.2f}")
col2.metric("Current Total", f"£{current_total:,.2f}")
col3.metric("Net Change", f"£{change_total:,.2f}")
col4.metric("Categories", category_count)
col5.metric("Adjustments", change_count)

st.subheader(f"Budget Breakdown for {selected_year}")
st.dataframe(
    budget_df,
    use_container_width=True,
    hide_index=True,
)

# ---- Adjustment history ----
history_df = pd.read_sql_query(
    """
    SELECT
        c.name AS category,
        a.old_amount,
        a.new_amount,
        a.change_amount,
        a.reason,
        a.changed_at
    FROM budget_adjustments a
    JOIN budget_lines b
        ON a.budget_line_id = b.id
    JOIN budget_categories c
        ON b.category_id = c.id
    JOIN budget_years y
        ON b.budget_year_id = y.id
    WHERE y.year = ?
    ORDER BY a.changed_at DESC
    """,
    con,
    params=(selected_year,),
)

st.subheader("Adjustment History")

if history_df.empty:
    st.info("No adjustments recorded for this year.")
else:
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )

con.close()