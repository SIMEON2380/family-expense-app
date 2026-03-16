import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    APP_TITLE: str = "Samtei Family Expense Tracker"

    DB_DIR: str = os.environ.get("FAMILY_BUDGET_DB_DIR", "data")
    DB_NAME: str = "family_budget.db"

    CATEGORIES = [
        "Rent",
        "Bills",
        "Food",
        "Transport",
        "Shopping",
        "School",
        "Medical",
        "Savings",
        "Other",
    ]

    EXPENSE_TYPES = [
        "Fixed",
        "Variable",
    ]

    FOOD_WARNING_PERCENT: int = 80
    DEFAULT_MONTHLY_LIMIT: float = 500.0