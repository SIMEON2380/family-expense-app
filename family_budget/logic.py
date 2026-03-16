import re
from io import BytesIO

import pandas as pd


def prepare_expense_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    out["expense_date"] = pd.to_datetime(out["expense_date"], errors="coerce")
    out["year"] = out["expense_date"].dt.year
    out["month_num"] = out["expense_date"].dt.month
    out["month_name"] = out["expense_date"].dt.strftime("%B")
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0)
    out["simeon_share"] = pd.to_numeric(out["simeon_share"], errors="coerce").fillna(0)
    out["bernice_share"] = pd.to_numeric(out["bernice_share"], errors="coerce").fillna(0)

    if "shop_name" in out.columns:
        out["shop_name"] = out["shop_name"].fillna("").astype(str)
    else:
        out["shop_name"] = ""

    return out


def get_monthly_totals(df: pd.DataFrame, year: int, month_name: str) -> dict:
    if df.empty:
        return {
            "total": 0.0,
            "fixed": 0.0,
            "variable": 0.0,
            "food": 0.0,
        }

    working = prepare_expense_dataframe(df)
    month_df = working[
        (working["year"] == year) &
        (working["month_name"] == month_name)
    ]

    total = float(month_df["amount"].sum()) if not month_df.empty else 0.0
    fixed = float(month_df.loc[month_df["expense_type"] == "Fixed", "amount"].sum()) if not month_df.empty else 0.0
    variable = float(month_df.loc[month_df["expense_type"] == "Variable", "amount"].sum()) if not month_df.empty else 0.0
    food = float(month_df.loc[month_df["category"] == "Food", "amount"].sum()) if not month_df.empty else 0.0

    return {
        "total": total,
        "fixed": fixed,
        "variable": variable,
        "food": food,
    }


def get_yearly_total(df: pd.DataFrame, year: int) -> float:
    if df.empty:
        return 0.0

    working = prepare_expense_dataframe(df)
    year_df = working[working["year"] == year]
    return float(year_df["amount"].sum()) if not year_df.empty else 0.0


def get_year_on_year_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year", "total", "prev_total", "growth_pct"])

    working = prepare_expense_dataframe(df)
    summary = (
        working.groupby("year", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total"})
        .sort_values("year")
    )

    summary["prev_total"] = summary["total"].shift(1)
    summary["growth_pct"] = ((summary["total"] - summary["prev_total"]) / summary["prev_total"]) * 100
    summary["growth_pct"] = summary["growth_pct"].round(2)

    return summary


def get_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year_month", "amount"])

    working = prepare_expense_dataframe(df)
    working["year_month"] = working["expense_date"].dt.strftime("%Y-%m")

    summary = (
        working.groupby("year_month", as_index=False)["amount"]
        .sum()
        .sort_values("year_month")
    )

    return summary


def get_food_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year_month", "amount"])

    working = prepare_expense_dataframe(df)
    working = working[working["category"] == "Food"].copy()

    if working.empty:
        return pd.DataFrame(columns=["year_month", "amount"])

    working["year_month"] = working["expense_date"].dt.strftime("%Y-%m")

    summary = (
        working.groupby("year_month", as_index=False)["amount"]
        .sum()
        .sort_values("year_month")
    )

    return summary


def get_shop_spend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "shop_name" not in df.columns:
        return pd.DataFrame(columns=["shop_name", "amount"])

    working = prepare_expense_dataframe(df)
    working["shop_name"] = working["shop_name"].fillna("").astype(str).str.strip()
    working = working[working["shop_name"] != ""]

    if working.empty:
        return pd.DataFrame(columns=["shop_name", "amount"])

    summary = (
        working.groupby("shop_name", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )

    return summary


def get_bill_growth_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["bill_name", "first_year", "latest_year", "first_amount", "latest_amount", "change_amount", "growth_pct"])

    working = prepare_expense_dataframe(df)

    grouped = (
        working.groupby(["year", "bill_name"], as_index=False)["amount"]
        .sum()
        .sort_values(["bill_name", "year"])
    )

    rows = []
    for bill_name, bill_df in grouped.groupby("bill_name"):
        bill_df = bill_df.sort_values("year")
        first = bill_df.iloc[0]
        latest = bill_df.iloc[-1]

        first_amount = float(first["amount"])
        latest_amount = float(latest["amount"])
        change_amount = latest_amount - first_amount

        if first_amount == 0:
            growth_pct = None
        else:
            growth_pct = round((change_amount / first_amount) * 100, 2)

        rows.append(
            {
                "bill_name": bill_name,
                "first_year": int(first["year"]),
                "latest_year": int(latest["year"]),
                "first_amount": first_amount,
                "latest_amount": latest_amount,
                "change_amount": change_amount,
                "growth_pct": growth_pct,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    return result.sort_values(["growth_pct", "change_amount"], ascending=[False, False], na_position="last")


def get_top_growth_insights(df: pd.DataFrame) -> list[str]:
    growth_df = get_bill_growth_summary(df)
    if growth_df.empty:
        return []

    insights = []
    for _, row in growth_df.head(5).iterrows():
        if pd.isna(row["growth_pct"]):
            continue
        insights.append(
            f"{row['bill_name']} moved from £{row['first_amount']:.2f} in {int(row['first_year'])} "
            f"to £{row['latest_amount']:.2f} in {int(row['latest_year'])} "
            f"({row['growth_pct']:.2f}% growth)."
        )
    return insights


def get_yearly_history_tables(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    working = prepare_expense_dataframe(df)

    working["expense_type_sort"] = working["expense_type"].map({"Fixed": 0, "Variable": 1}).fillna(2)
    working = working.sort_values(
        ["year", "expense_type_sort", "bill_name", "expense_date", "id"],
        ascending=[False, True, True, False, False],
    )

    year_tables = {}
    for year, year_df in working.groupby("year", sort=False):
        display_df = year_df.copy()

        preferred_columns = [
            "expense_date",
            "bill_name",
            "shop_name",
            "amount",
            "simeon_share",
            "bernice_share",
            "category",
            "expense_type",
            "comments",
        ]

        existing_columns = [col for col in preferred_columns if col in display_df.columns]
        display_df = display_df[existing_columns].copy()

        year_tables[int(year)] = display_df

    return year_tables


def build_yearly_budget_from_source(source_df: pd.DataFrame, target_year: int, increase_pct: float) -> pd.DataFrame:
    if source_df.empty:
        return pd.DataFrame(
            columns=[
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
        )

    working = source_df.copy()

    working["bill_name"] = working["bill_name"].fillna("").astype(str).str.upper()
    working["shop_name"] = working.get("shop_name", "").fillna("").astype(str)
    working["amount"] = pd.to_numeric(working["amount"], errors="coerce").fillna(0.0)
    working["comments"] = working["comments"].fillna("").astype(str)
    working["category"] = working["category"].fillna("Other").astype(str)
    working["expense_type"] = working["expense_type"].fillna("Fixed").astype(str)

    multiplier = 1 + (increase_pct / 100.0)
    working["amount"] = (working["amount"] * multiplier).round(2)

    working["simeon_share"] = (working["amount"] / 2).round(2)
    working["bernice_share"] = (working["amount"] - working["simeon_share"]).round(2)

    working["expense_date"] = f"{target_year}-01-01"

    final_cols = [
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

    for col in final_cols:
        if col not in working.columns:
            working[col] = ""

    return working[final_cols].copy()


def categorise_bill_name(bill_name: str) -> str:
    name = str(bill_name).strip().lower()

    if "food" in name:
        return "Food"
    if "mortage" in name or "mortgage" in name or "rent" in name:
        return "Rent"
    if "council tax" in name or "water" in name or "gas" in name or "electric" in name:
        return "Bills"
    if "virgin media" in name or "tv licence" in name or "ee phone" in name or "verisure" in name or "greenbelt" in name or "insurance" in name:
        return "Bills"
    if "children" in name:
        return "School"
    if "window cleaning" in name:
        return "Other"
    if "sofa" in name or "bed" in name:
        return "Shopping"

    return "Other"


def classify_expense_type(bill_name: str, category: str) -> str:
    name = str(bill_name).strip().lower()

    variable_names = {"food", "window cleaning"}
    if category == "Food":
        return "Variable"
    if name in variable_names:
        return "Variable"

    return "Fixed"


def parse_budget_excel(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()

    raw_bytes = uploaded_file.read()
    excel_file = pd.ExcelFile(BytesIO(raw_bytes))

    all_rows = []

    for sheet_name in excel_file.sheet_names:
        if not re.fullmatch(r"\d{4}", str(sheet_name).strip()):
            continue

        year = int(str(sheet_name).strip())
        df = pd.read_excel(BytesIO(raw_bytes), sheet_name=sheet_name, header=0)

        if df.empty:
            continue

        first_cols = list(df.columns[:5])
        df = df[first_cols].copy()

        rename_map = {}
        if len(first_cols) >= 1:
            rename_map[first_cols[0]] = "bill_name"
        if len(first_cols) >= 2:
            rename_map[first_cols[1]] = "amount"
        if len(first_cols) >= 3:
            rename_map[first_cols[2]] = "simeon_share"
        if len(first_cols) >= 4:
            rename_map[first_cols[3]] = "bernice_share"
        if len(first_cols) >= 5:
            rename_map[first_cols[4]] = "comments"

        df = df.rename(columns=rename_map)

        for col in ["bill_name", "amount", "simeon_share", "bernice_share", "comments"]:
            if col not in df.columns:
                df[col] = None

        df["bill_name"] = df["bill_name"].astype(str).str.strip().str.upper()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["simeon_share"] = pd.to_numeric(df["simeon_share"], errors="coerce").fillna(0)
        df["bernice_share"] = pd.to_numeric(df["bernice_share"], errors="coerce").fillna(0)
        df["comments"] = df["comments"].fillna("").astype(str).str.strip()

        df = df[df["bill_name"].notna()]
        df = df[df["bill_name"] != ""]
        df = df[df["amount"].notna()]
        df = df[~df["bill_name"].str.lower().isin(["total", "totals"])]
        df = df[~df["bill_name"].str.lower().str.startswith("total savings")]
        df = df[~df["bill_name"].str.lower().str.startswith("from ")]
        df = df[df["amount"] > 0]

        if df.empty:
            continue

        df["expense_date"] = f"{year}-01-01"
        df["shop_name"] = ""
        df["category"] = df["bill_name"].apply(categorise_bill_name)
        df["expense_type"] = df.apply(
            lambda row: classify_expense_type(row["bill_name"], row["category"]),
            axis=1,
        )

        final_df = df[
            [
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
        ].copy()

        all_rows.append(final_df)

    if not all_rows:
        return pd.DataFrame(
            columns=[
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
        )

    return pd.concat(all_rows, ignore_index=True)