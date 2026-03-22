import os
import sqlite3
from typing import Optional

import pandas as pd


def make_db(cfg):
    db_path = os.path.join(cfg.DB_DIR, cfg.DB_NAME)

    def get_conn():
        os.makedirs(cfg.DB_DIR, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def column_exists(cur, table_name: str, column_name: str) -> bool:
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = cur.fetchall()
        return any(col["name"] == column_name for col in cols)

    def ensure_schema():
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                bill_name TEXT NOT NULL,
                shop_name TEXT DEFAULT '',
                amount REAL NOT NULL DEFAULT 0,
                simeon_share REAL NOT NULL DEFAULT 0,
                bernice_share REAL NOT NULL DEFAULT 0,
                comments TEXT,
                category TEXT NOT NULL DEFAULT 'Other',
                expense_type TEXT NOT NULL DEFAULT 'Variable',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                monthly_limit REAL NOT NULL DEFAULT 500,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(month, year)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_name TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                simeon_share REAL NOT NULL DEFAULT 0,
                bernice_share REAL NOT NULL DEFAULT 0,
                comments TEXT,
                category TEXT NOT NULL DEFAULT 'Other',
                expense_type TEXT NOT NULL DEFAULT 'Fixed',
                frequency TEXT NOT NULL DEFAULT 'Monthly',
                day_of_month INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_years (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_year_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                original_amount REAL NOT NULL DEFAULT 0,
                current_amount REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (budget_year_id) REFERENCES budget_years(id),
                FOREIGN KEY (category_id) REFERENCES budget_categories(id),
                UNIQUE(budget_year_id, category_id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budget_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_line_id INTEGER NOT NULL,
                old_amount REAL NOT NULL,
                new_amount REAL NOT NULL,
                change_amount REAL NOT NULL,
                reason TEXT,
                changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (budget_line_id) REFERENCES budget_lines(id)
            )
            """
        )

        cur.execute(
            """
            INSERT OR IGNORE INTO budget_categories (name) VALUES
            ('Rent'),
            ('Groceries'),
            ('Transport'),
            ('Utilities'),
            ('School'),
            ('Savings'),
            ('Other')
            """
        )

        if not column_exists(cur, "expenses", "shop_name"):
            cur.execute("ALTER TABLE expenses ADD COLUMN shop_name TEXT DEFAULT ''")

        conn.commit()
        conn.close()

    def add_expense(
        expense_date: str,
        bill_name: str,
        shop_name: str,
        amount: float,
        simeon_share: float,
        bernice_share: float,
        comments: str,
        category: str,
        expense_type: str,
    ):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO expenses (
                expense_date,
                bill_name,
                shop_name,
                amount,
                simeon_share,
                bernice_share,
                comments,
                category,
                expense_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                expense_date,
                bill_name,
                shop_name,
                amount,
                simeon_share,
                bernice_share,
                comments,
                category,
                expense_type,
            ),
        )

        conn.commit()
        conn.close()

    def bulk_insert_expenses(df: pd.DataFrame):
        if df.empty:
            return 0

        conn = get_conn()
        cur = conn.cursor()

        if "shop_name" not in df.columns:
            df = df.copy()
            df["shop_name"] = ""

        rows = []
        for _, row in df.iterrows():
            rows.append(
                (
                    str(row["expense_date"]),
                    str(row["bill_name"]),
                    str(row["shop_name"]) if pd.notna(row["shop_name"]) else "",
                    float(row["amount"]),
                    float(row["simeon_share"]),
                    float(row["bernice_share"]),
                    str(row["comments"]) if pd.notna(row["comments"]) else "",
                    str(row["category"]),
                    str(row["expense_type"]),
                )
            )

        cur.executemany(
            """
            INSERT INTO expenses (
                expense_date,
                bill_name,
                shop_name,
                amount,
                simeon_share,
                bernice_share,
                comments,
                category,
                expense_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        conn.commit()
        conn.close()
        return len(rows)

    def read_all_expenses() -> pd.DataFrame:
        conn = get_conn()
        df = pd.read_sql_query(
            """
            SELECT *
            FROM expenses
            ORDER BY expense_date DESC, expense_type ASC, bill_name ASC, id DESC
            """,
            conn,
        )
        conn.close()
        return df

    def read_expenses_by_year(year: int) -> pd.DataFrame:
        conn = get_conn()
        df = pd.read_sql_query(
            """
            SELECT *
            FROM expenses
            WHERE substr(expense_date, 1, 4) = ?
            ORDER BY expense_type ASC, bill_name ASC, expense_date ASC, id ASC
            """,
            conn,
            params=(str(year),),
        )
        conn.close()
        return df

    def delete_expense(expense_id: int):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()

    def clear_all_expenses():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses")
        conn.commit()
        conn.close()

    def delete_expenses_by_year(year: int):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM expenses WHERE substr(expense_date, 1, 4) = ?",
            (str(year),),
        )
        conn.commit()
        conn.close()

    def get_existing_years() -> list[int]:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT substr(expense_date, 1, 4) AS year
            FROM expenses
            WHERE expense_date IS NOT NULL
            ORDER BY year
            """
        )
        rows = cur.fetchall()
        conn.close()
        years = []
        for row in rows:
            if row["year"] and str(row["year"]).isdigit():
                years.append(int(row["year"]))
        return years

    def year_exists(year: int) -> bool:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM expenses
            WHERE substr(expense_date, 1, 4) = ?
            """,
            (str(year),),
        )
        row = cur.fetchone()
        conn.close()
        return row["row_count"] > 0

    def save_budget(month: str, year: int, monthly_limit: float):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO budget_settings (month, year, monthly_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(month, year)
            DO UPDATE SET monthly_limit = excluded.monthly_limit
            """,
            (month, year, monthly_limit),
        )

        conn.commit()
        conn.close()

    def get_budget(month: str, year: int) -> Optional[float]:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT monthly_limit
            FROM budget_settings
            WHERE month = ? AND year = ?
            """,
            (month, year),
        )
        row = cur.fetchone()
        conn.close()

        return row["monthly_limit"] if row else None

    def add_recurring_expense(
        bill_name: str,
        amount: float,
        simeon_share: float,
        bernice_share: float,
        comments: str,
        category: str,
        expense_type: str,
        frequency: str,
        day_of_month: int,
        is_active: int = 1,
    ):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO recurring_expenses (
                bill_name,
                amount,
                simeon_share,
                bernice_share,
                comments,
                category,
                expense_type,
                frequency,
                day_of_month,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill_name,
                amount,
                simeon_share,
                bernice_share,
                comments,
                category,
                expense_type,
                frequency,
                day_of_month,
                is_active,
            ),
        )

        conn.commit()
        conn.close()

    def read_all_recurring_expenses() -> pd.DataFrame:
        conn = get_conn()
        df = pd.read_sql_query(
            """
            SELECT *
            FROM recurring_expenses
            ORDER BY bill_name ASC, id DESC
            """,
            conn,
        )
        conn.close()
        return df

    def delete_recurring_expense(recurring_id: int):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM recurring_expenses WHERE id = ?", (recurring_id,))
        conn.commit()
        conn.close()

    def generate_recurring_for_month(year: int, month: int):
        conn = get_conn()
        cur = conn.cursor()

        recurring_df = pd.read_sql_query(
            """
            SELECT *
            FROM recurring_expenses
            WHERE is_active = 1 AND frequency = 'Monthly'
            ORDER BY id ASC
            """,
            conn,
        )

        inserted = 0
        skipped = 0

        for _, row in recurring_df.iterrows():
            day = int(row["day_of_month"])
            if day < 1:
                day = 1
            if day > 28:
                day = 28

            expense_date = f"{year}-{month:02d}-{day:02d}"

            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM expenses
                WHERE bill_name = ?
                  AND substr(expense_date, 1, 7) = ?
                """,
                (row["bill_name"], f"{year}-{month:02d}"),
            )
            existing = cur.fetchone()

            if existing["row_count"] > 0:
                skipped += 1
                continue

            cur.execute(
                """
                INSERT INTO expenses (
                    expense_date,
                    bill_name,
                    shop_name,
                    amount,
                    simeon_share,
                    bernice_share,
                    comments,
                    category,
                    expense_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    expense_date,
                    str(row["bill_name"]).upper(),
                    "",
                    float(row["amount"]),
                    float(row["simeon_share"]),
                    float(row["bernice_share"]),
                    row["comments"],
                    row["category"],
                    row["expense_type"],
                ),
            )
            inserted += 1

        conn.commit()
        conn.close()

        return {
            "inserted": inserted,
            "skipped": skipped,
        }

    return {
        "db_path": db_path,
        "ensure_schema": ensure_schema,
        "add_expense": add_expense,
        "bulk_insert_expenses": bulk_insert_expenses,
        "read_all_expenses": read_all_expenses,
        "read_expenses_by_year": read_expenses_by_year,
        "delete_expense": delete_expense,
        "clear_all_expenses": clear_all_expenses,
        "delete_expenses_by_year": delete_expenses_by_year,
        "get_existing_years": get_existing_years,
        "year_exists": year_exists,
        "save_budget": save_budget,
        "get_budget": get_budget,
        "add_recurring_expense": add_recurring_expense,
        "read_all_recurring_expenses": read_all_recurring_expenses,
        "delete_recurring_expense": delete_recurring_expense,
        "generate_recurring_for_month": generate_recurring_for_month,
    }