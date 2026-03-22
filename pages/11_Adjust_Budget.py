import streamlit as st
import pandas as pd
import sqlite3

from family_budget.config import Config
from family_budget.db import make_db

cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title="Adjust Budget", layout="wide")

st.title("🔧 Adjust Budget")

DB["ensure_schema"]()

con = sqlite3.connect(DB["db_path"])
cur = con.cursor()

# ---- Select Year ----
years_df = pd.read_sql_query("SELECT * FROM budget_years ORDER BY year DESC", con)

if years_df.empty:
    st.warning("No budget years found")
    st.stop()

selected_year = st.selectbox("Select Year", years_df["year"])

year_id = cur.execute(
    "SELECT id FROM budget_years WHERE year = ?", (selected_year,)
).fetchone()[0]

# ---- Load Categories with budget ----
df = pd.read_sql_query(
    """
    SELECT b.id, c.name, b.current_amount
    FROM budget_lines b
    JOIN budget_categories c ON b.category_id = c.id
    WHERE b.budget_year_id = ?
    """,
    con,
    params=(year_id,),
)

if df.empty:
    st.warning("No budget found for this year. Set it first.")
    st.stop()

# ---- Select Category ----
category = st.selectbox("Select Category", df["name"])

row = df[df["name"] == category].iloc[0]

current_amount = row["current_amount"]
budget_line_id = row["id"]

st.info(f"Current Amount: £{current_amount}")

# ---- Adjustment Form ----
new_amount = st.number_input("New Amount", min_value=0.0, step=50.0)
reason = st.text_input("Reason for change")

if st.button("Apply Adjustment"):
    change = new_amount - current_amount

    # 1. Insert into history
    cur.execute(
        """
        INSERT INTO budget_adjustments (
            budget_line_id,
            old_amount,
            new_amount,
            change_amount,
            reason
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (budget_line_id, current_amount, new_amount, change, reason),
    )

    # 2. Update current value
    cur.execute(
        """
        UPDATE budget_lines
        SET current_amount = ?
        WHERE id = ?
        """,
        (new_amount, budget_line_id),
    )

    con.commit()

    st.success("Budget updated successfully")
    st.rerun()

# ---- Show Adjustment History ----
st.subheader("Adjustment History")

history_df = pd.read_sql_query(
    """
    SELECT c.name, a.old_amount, a.new_amount, a.change_amount, a.reason, a.changed_at
    FROM budget_adjustments a
    JOIN budget_lines b ON a.budget_line_id = b.id
    JOIN budget_categories c ON b.category_id = c.id
    JOIN budget_years y ON b.budget_year_id = y.id
    WHERE y.year = ?
    ORDER BY a.changed_at DESC
    """,
    con,
    params=(selected_year,),
)

if not history_df.empty:
    st.dataframe(history_df)
else:
    st.info("No adjustments made yet")

con.close()