import streamlit as st
import pandas as pd

from family_budget.config import Config
from family_budget.db import make_db

cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title="Annual Budget", layout="wide")

st.title("📊 Annual Budget")

DB["ensure_schema"]()

conn = DB["db_path"]

# ---- Get Years ----
conn = DB["db_path"]
import sqlite3
con = sqlite3.connect(conn)
cur = con.cursor()

years_df = pd.read_sql_query("SELECT * FROM budget_years ORDER BY year DESC", con)

if years_df.empty:
    st.warning("No budget years found. Create one below.")
else:
    selected_year = st.selectbox("Select Year", years_df["year"])

# ---- Create Year ----
st.subheader("Create New Year")

new_year = st.number_input("Enter Year", min_value=2020, max_value=2100, step=1)

if st.button("Create Year"):
    try:
        cur.execute("INSERT INTO budget_years (year) VALUES (?)", (int(new_year),))
        con.commit()
        st.success(f"Year {new_year} created")
        st.rerun()
    except:
        st.warning("Year already exists")

# ---- Load Categories ----
categories_df = pd.read_sql_query("SELECT * FROM budget_categories", con)

# ---- Budget Input ----
st.subheader("Set Budget for Selected Year")

if not years_df.empty:
    year_id = cur.execute(
        "SELECT id FROM budget_years WHERE year = ?", (selected_year,)
    ).fetchone()[0]

    budget_data = []

    for _, row in categories_df.iterrows():
        category = row["name"]

        amount = st.number_input(
            f"{category} Budget",
            min_value=0.0,
            step=50.0,
            key=f"{category}",
        )

        budget_data.append((year_id, row["id"], amount))

    if st.button("Save Budget"):
        for year_id, category_id, amount in budget_data:
            cur.execute(
                """
                INSERT INTO budget_lines (budget_year_id, category_id, original_amount, current_amount)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(budget_year_id, category_id)
                DO UPDATE SET current_amount = excluded.current_amount
                """,
                (year_id, category_id, amount, amount),
            )

        con.commit()
        st.success("Budget saved successfully")

# ---- Show Budget ----
st.subheader("Current Budget")

if not years_df.empty:
    df = pd.read_sql_query(
        """
        SELECT c.name, b.original_amount, b.current_amount
        FROM budget_lines b
        JOIN budget_categories c ON b.category_id = c.id
        JOIN budget_years y ON b.budget_year_id = y.id
        WHERE y.year = ?
        """,
        con,
        params=(selected_year,),
    )

    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No budget set yet for this year")

con.close()