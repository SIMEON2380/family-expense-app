import re
import sqlite3

import pandas as pd
import streamlit as st

from family_budget.config import Config
from family_budget.db import make_db

cfg = Config()
DB = make_db(cfg)

st.set_page_config(page_title="Import Budget Excel", layout="wide")
st.title("📥 Import Budget Excel")

DB["ensure_schema"]()


def normalise_bill_name(name: str) -> str:
    if pd.isna(name):
        return ""

    value = str(name).strip()

    replacements = {
        "Mortage": "Mortgage",
        "Tv licence": "TV Licence",
        "TV licence": "TV Licence",
        "Virign water": "Virgin Water (Outtrap)",
        "Virign water(Outtrap)": "Virgin Water (Outtrap)",
        "Virign water (Outtrap)": "Virgin Water (Outtrap)",
        "Virgin water": "Virgin Water (Outtrap)",
        "Virgin water(Outtrap)": "Virgin Water (Outtrap)",
        "Virgin water (Outtrap)": "Virgin Water (Outtrap)",
        "Children development": "Children Development",
        "Sofa": "Sofa (V12 Finance)",
        "Sofa(V12 Finance)": "Sofa (V12 Finance)",
        "Sofa (V12 Finance)": "Sofa (V12 Finance)",
    }

    value = replacements.get(value, value)

    cleanup_patterns = [
        (r"^Council Tax.*", "Council Tax"),
        (r"^Greenbelt.*", "Greenbelt"),
        (r"^EE Phone.*", "EE Phone"),
        (r"^Children development.*", "Children Development"),
        (r"^Children Development.*", "Children Development"),
        (r"^Virgin water.*", "Virgin Water (Outtrap)"),
        (r"^Virign water.*", "Virgin Water (Outtrap)"),
        (r"^Sofa.*", "Sofa (V12 Finance)"),
    ]

    for pattern, replacement in cleanup_patterns:
        if re.match(pattern, value, flags=re.IGNORECASE):
            return replacement

    return value.strip()


def find_matching_column(df: pd.DataFrame, possible_names: list[str]):
    lower_map = {str(col).strip().lower(): col for col in df.columns}
    for name in possible_names:
        key = name.strip().lower()
        if key in lower_map:
            return lower_map[key]
    return None


def parse_budget_sheet(df: pd.DataFrame, year: int) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    bill_col = find_matching_column(df, ["Bill Name", "Bill", "Name"])
    amount_col = find_matching_column(df, ["Amount", "Budget", "Original Amount"])
    midyear_col = find_matching_column(
        df,
        ["Mid Year adjustments", "Mid Year Adjustment", "Adjustment", "Adjusted Amount"],
    )
    comments_col = find_matching_column(df, ["Comments", "Comment", "Notes"])

    if bill_col is None or amount_col is None:
        return pd.DataFrame()

    parsed_rows = []

    for _, row in df.iterrows():
        raw_bill_name = row.get(bill_col)
        raw_amount = row.get(amount_col)

        bill_name = normalise_bill_name(raw_bill_name)

        if not bill_name:
            continue

        if pd.isna(raw_amount) or str(raw_amount).strip() == "":
            continue

        amount_text = str(raw_amount).replace("£", "").replace(",", "").strip()
        try:
            original_amount = float(amount_text)
        except ValueError:
            continue

        current_amount = original_amount
        if midyear_col is not None:
            raw_midyear = row.get(midyear_col)
            if not pd.isna(raw_midyear) and str(raw_midyear).strip() != "":
                midyear_text = str(raw_midyear).replace("£", "").replace(",", "").strip()
                try:
                    current_amount = float(midyear_text)
                except ValueError:
                    current_amount = original_amount

        comments = ""
        if comments_col is not None and not pd.isna(row.get(comments_col)):
            comments = str(row.get(comments_col)).strip()

        parsed_rows.append(
            {
                "year": year,
                "bill_name": bill_name,
                "original_amount": original_amount,
                "current_amount": current_amount,
                "comments": comments,
            }
        )

    if not parsed_rows:
        return pd.DataFrame()

    result = pd.DataFrame(parsed_rows)
    result = result.drop_duplicates(subset=["year", "bill_name"], keep="last")
    result = result.sort_values(["year", "bill_name"]).reset_index(drop=True)
    return result


def import_budget_dataframe(df: pd.DataFrame) -> tuple[int, int]:
    con = sqlite3.connect(DB["db_path"])
    cur = con.cursor()

    imported_count = 0
    adjustment_count = 0

    for _, row in df.iterrows():
        year = int(row["year"])
        bill_name = str(row["bill_name"]).strip()
        original_amount = float(row["original_amount"])
        current_amount = float(row["current_amount"])

        cur.execute(
            """
            INSERT OR IGNORE INTO budget_years (year)
            VALUES (?)
            """,
            (year,),
        )

        cur.execute(
            """
            INSERT OR IGNORE INTO budget_categories (name)
            VALUES (?)
            """,
            (bill_name,),
        )

        cur.execute("SELECT id FROM budget_years WHERE year = ?", (year,))
        budget_year_id = cur.fetchone()[0]

        cur.execute("SELECT id FROM budget_categories WHERE name = ?", (bill_name,))
        category_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT id
            FROM budget_lines
            WHERE budget_year_id = ? AND category_id = ?
            """,
            (budget_year_id, category_id),
        )
        existing = cur.fetchone()

        if existing is None:
            cur.execute(
                """
                INSERT INTO budget_lines (
                    budget_year_id,
                    category_id,
                    original_amount,
                    current_amount
                )
                VALUES (?, ?, ?, ?)
                """,
                (budget_year_id, category_id, original_amount, current_amount),
            )
            budget_line_id = cur.lastrowid
        else:
            budget_line_id = existing[0]
            cur.execute(
                """
                UPDATE budget_lines
                SET original_amount = ?, current_amount = ?
                WHERE id = ?
                """,
                (original_amount, current_amount, budget_line_id),
            )

        imported_count += 1

        if current_amount != original_amount:
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
                (
                    budget_line_id,
                    original_amount,
                    current_amount,
                    current_amount - original_amount,
                    "Imported from Excel mid-year adjustment",
                ),
            )
            adjustment_count += 1

    con.commit()
    con.close()

    return imported_count, adjustment_count


uploaded_file = st.file_uploader("Upload budget Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        with st.spinner("Reading workbook..."):
            excel_file = pd.ExcelFile(uploaded_file, engine="openpyxl")
            st.write("Sheets found:", excel_file.sheet_names)

            year_sheets: dict[int, pd.DataFrame] = {}

            for sheet_name in excel_file.sheet_names:
                sheet_name_clean = str(sheet_name).strip()
                if sheet_name_clean.isdigit() and len(sheet_name_clean) == 4:
                    sheet_df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        engine="openpyxl",
                    )
                    year_sheets[int(sheet_name_clean)] = sheet_df

    except Exception as exc:
        st.error(f"Could not read Excel file: {exc}")
        st.stop()

    if not year_sheets:
        st.warning("No year sheets found. Sheet names should look like 2024, 2025, 2026.")
        st.stop()

    all_parsed = []
    progress = st.progress(0, text="Parsing sheets...")

    total_sheets = len(year_sheets)
    for index, (year, sheet_df) in enumerate(sorted(year_sheets.items()), start=1):
        parsed_df = parse_budget_sheet(sheet_df, year)

        st.subheader(f"Preview: {year}")
        if parsed_df.empty:
            st.info("No valid budget rows found on this sheet.")
        else:
            st.dataframe(parsed_df, use_container_width=True, hide_index=True)
            all_parsed.append(parsed_df)

        progress.progress(int(index / total_sheets * 100), text=f"Parsed {year}")

    if all_parsed:
        combined_df = pd.concat(all_parsed, ignore_index=True)

        st.subheader("Import Summary")
        st.write(f"Years found: {combined_df['year'].nunique()}")
        st.write(f"Rows ready to import: {len(combined_df)}")

        if st.button("Import Budget Data"):
            with st.spinner("Importing budget data into database..."):
                imported_count, adjustment_count = import_budget_dataframe(combined_df)

            st.success(
                f"Import complete. {imported_count} budget rows processed and "
                f"{adjustment_count} adjustment history rows created."
            )
    else:
        st.warning("Nothing valid was found to import.")