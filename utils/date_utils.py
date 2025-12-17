"""
כלי עזר לניהול תאריכים ורבעונים
"""

from datetime import datetime
from typing import Tuple


def get_current_quarter() -> str:
    """
    מחשב את הרבעון הנוכחי לפי החודש

    Returns:
        str: Q1, Q2, Q3, או Q4
    """
    month = datetime.now().month

    if 1 <= month <= 3:
        return "Q1"
    elif 4 <= month <= 6:
        return "Q2"
    elif 7 <= month <= 9:
        return "Q3"
    else:  # 10-12
        return "Q4"


def get_current_year() -> int:
    """
    מחזיר את השנה הנוכחית

    Returns:
        int: השנה הנוכחית
    """
    return datetime.now().year


def get_quarter_and_year(quarter: str = None, year: int = None) -> Tuple[str, int]:
    """
    מחזיר רבעון ושנה - נוכחיים או מוגדרים

    Args:
        quarter: רבעון (Q1-Q4) או None לאוטומטי
        year: שנה או None לאוטומטי

    Returns:
        Tuple[str, int]: (רבעון, שנה)
    """
    if quarter is None:
        quarter = get_current_quarter()
    else:
        # ולידציה
        if quarter not in ["Q1", "Q2", "Q3", "Q4"]:
            raise ValueError(f"רבעון לא תקין: {quarter}. חייב להיות Q1, Q2, Q3 או Q4")

    if year is None:
        year = get_current_year()
    else:
        # ולידציה
        if not (2000 <= year <= 2100):
            raise ValueError(f"שנה לא תקינה: {year}")

    return quarter, year


def quarter_to_month(quarter: str) -> int:
    """
    ממיר רבעון לחודש אמצע (לצורך חישובים)

    Args:
        quarter: Q1-Q4

    Returns:
        int: חודש אמצע הרבעון
    """
    mapping = {
        "Q1": 2,   # פברואר
        "Q2": 5,   # מאי
        "Q3": 8,   # אוגוסט
        "Q4": 11   # נובמבר
    }
    return mapping.get(quarter, 11)


def get_quarters_elapsed(quarter: str) -> int:
    """
    מחזיר את מספר הרבעונים שחלפו בשנה הנוכחית

    Args:
        quarter: Q1-Q4

    Returns:
        int: מספר רבעונים (0-3)
    """
    mapping = {
        "Q1": 1,
        "Q2": 2,
        "Q3": 3,
        "Q4": 4
    }
    return mapping.get(quarter, 4)


def format_fund_name(quarter: str, year: int, index_name: str = None) -> str:
    """
    יוצר שם לקרן בפורמט סטנדרטי

    Args:
        quarter: רבעון (Q1-Q4)
        year: שנה
        index_name: שם המדד (TASE125 או SP500) - אופציונלי

    Returns:
        str: שם הקרן, לדוגמה: "Fund_10_Q4_2025" או "Fund_10_TASE_Q4_2025"
    """
    if index_name:
        return f"Fund_10_{index_name}_{quarter}_{year}"
    return f"Fund_10_{quarter}_{year}"


def get_current_date_string() -> str:
    """
    מחזיר תאריך נוכחי בפורמט ISO

    Returns:
        str: תאריך בפורמט YYYY-MM-DD
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_years_range(base_year: int, num_years: int = 5) -> list:
    """
    מחזיר רשימת שנים אחורה מהשנה הבסיסית

    Args:
        base_year: שנת בסיס
        num_years: מספר שנים אחורה

    Returns:
        list: רשימת שנים (מהחדש לישן)
    """
    return list(range(base_year, base_year - num_years, -1))
