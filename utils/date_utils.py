"""
כלי עזר לניהול תאריכים ורבעונים
"""

from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional


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


def _quarter_sort_key(quarter: str, year: int) -> int:
    """
    מחזיר מפתח מיון למיון רבעונים כרונולוגית

    Args:
        quarter: Q1-Q4
        year: שנה

    Returns:
        int: מפתח מיון (year * 10 + quarter_num)
    """
    q_num = int(quarter[1])
    return year * 10 + q_num


def get_fund_output_dir(base_output_dir: Path, index_name: str, quarter: str, year: int) -> Path:
    """
    מחזיר תיקיית פלט לקרן לפי מדד ורבעון

    Args:
        base_output_dir: תיקיית הפלט הבסיסית (Fund_Docs)
        index_name: שם המדד (SP500 או TASE125)
        quarter: רבעון (Q1-Q4)
        year: שנה

    Returns:
        Path: נתיב לתיקיה, לדוגמה: Fund_Docs/SP500/Q1_2026
    """
    return base_output_dir / index_name / f"{quarter}_{year}"


def find_latest_fund_dir(base_output_dir: Path, index_name: str) -> Optional[Path]:
    """
    מוצא את תיקיית הקרן האחרונה למדד נתון

    סורק תיקיות ברמת Fund_Docs/{INDEX}/ וממיין לפי רבעון ושנה.

    Args:
        base_output_dir: תיקיית הפלט הבסיסית (Fund_Docs)
        index_name: שם המדד (SP500 או TASE125)

    Returns:
        Optional[Path]: נתיב לתיקייה האחרונה, או None אם לא נמצאה
    """
    index_dir = base_output_dir / index_name
    if not index_dir.exists():
        return None

    quarter_dirs = []
    for d in index_dir.iterdir():
        if not d.is_dir():
            continue
        # Parse folder name: Q1_2026, Q4_2025, etc.
        parts = d.name.split("_")
        if len(parts) == 2 and parts[0] in ("Q1", "Q2", "Q3", "Q4"):
            try:
                year = int(parts[1])
                quarter_dirs.append((d, _quarter_sort_key(parts[0], year)))
            except ValueError:
                continue

    if not quarter_dirs:
        return None

    # Sort by key descending, return latest
    quarter_dirs.sort(key=lambda x: x[1], reverse=True)
    return quarter_dirs[0][0]


def find_previous_fund_dir(base_output_dir: Path, index_name: str, current_quarter: str, current_year: int) -> Optional[Path]:
    """
    מוצא את תיקיית הקרן הקודמת (לפני הרבעון הנוכחי)

    Args:
        base_output_dir: תיקיית הפלט הבסיסית (Fund_Docs)
        index_name: שם המדד
        current_quarter: הרבעון הנוכחי
        current_year: השנה הנוכחית

    Returns:
        Optional[Path]: נתיב לתיקייה הקודמת, או None
    """
    index_dir = base_output_dir / index_name
    if not index_dir.exists():
        return None

    current_key = _quarter_sort_key(current_quarter, current_year)

    quarter_dirs = []
    for d in index_dir.iterdir():
        if not d.is_dir():
            continue
        parts = d.name.split("_")
        if len(parts) == 2 and parts[0] in ("Q1", "Q2", "Q3", "Q4"):
            try:
                year = int(parts[1])
                key = _quarter_sort_key(parts[0], year)
                if key < current_key:
                    quarter_dirs.append((d, key))
            except ValueError:
                continue

    if not quarter_dirs:
        return None

    quarter_dirs.sort(key=lambda x: x[1], reverse=True)
    return quarter_dirs[0][0]
