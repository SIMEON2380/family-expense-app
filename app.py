import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db


cfg = Config()
DB = make_db(cfg)

st.set_page_config(
    page_title=cfg.APP_TITLE,
    layout="wide",
)

DB["ensure_schema"]()

st.title("🏠 Samtei Family Expense Tracker")
st.write("Welcome to the Family Expense Tracker.")
st.info("Use the menu on the left to navigate the app.")