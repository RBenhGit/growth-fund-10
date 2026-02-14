"""
מנתח קובצי Update.md לחילוץ מניות מדורגות והרכב קרן

משמש לזיהוי מניות לעדכון רבעוני מתוך קובץ ה-Update.md של הרבעון הקודם.
"""

import re
from pathlib import Path
from typing import Optional
from utils.date_utils import find_latest_fund_dir


def parse_update_file(filepath: Path, top_base: int = 30, top_potential: int = 20) -> dict:
    """
    מנתח קובץ Update.md ומחלץ מניות מדורגות והרכב קרן

    Args:
        filepath: נתיב לקובץ Update.md
        top_base: מספר מניות בסיס עליונות לחילוץ
        top_potential: מספר מניות פוטנציאל עליונות לחילוץ

    Returns:
        dict עם:
            base_candidates: רשימת מניות בסיס מדורגות
            potential_candidates: רשימת מניות פוטנציאל מדורגות
            selected_stocks: הרכב הקרן הסופי
            fund_name: שם הקרן
            date: תאריך העדכון
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # Extract fund name from title
    fund_name = ""
    date = ""
    for line in lines:
        if line.startswith("# עדכון קרן "):
            fund_name = line.replace("# עדכון קרן ", "").strip()
        elif line.startswith("תאריך עדכון:"):
            date = line.replace("תאריך עדכון:", "").strip()

    # Parse sections
    base_candidates = _parse_ranked_table(content, "## מניות בסיס מדורגות", top_base)
    potential_candidates = _parse_ranked_table(content, "## מניות פוטנציאל מדורגות", top_potential)
    selected_stocks = _parse_composition_table(content)

    return {
        "base_candidates": base_candidates,
        "potential_candidates": potential_candidates,
        "selected_stocks": selected_stocks,
        "fund_name": fund_name,
        "date": date,
    }


def _parse_ranked_table(content: str, section_header: str, limit: int) -> list[dict]:
    """
    מנתח טבלת מניות מדורגות (בסיס או פוטנציאל)

    Format: | דירוג | שם חברה | סימול | ציון |
    """
    results = []

    # Find section
    idx = content.find(section_header)
    if idx == -1:
        return results

    # Get lines after header
    section_text = content[idx:]
    lines = section_text.split("\n")

    # Skip header line, table header, and separator
    in_table = False
    for line in lines[1:]:
        line = line.strip()

        # Detect table header row
        if line.startswith("| דירוג"):
            in_table = True
            continue

        # Skip separator row
        if line.startswith("|---") or line.startswith("| ---"):
            continue

        # End of table
        if in_table and (not line.startswith("|") or line.startswith("##")):
            break

        if not in_table or not line.startswith("|"):
            continue

        # Parse row: | rank | name | symbol | score |
        cells = [c.strip() for c in line.split("|")]
        # Split produces ['', rank, name, symbol, score, '']
        cells = [c for c in cells if c]

        if len(cells) >= 4:
            try:
                results.append({
                    "rank": int(cells[0]),
                    "name": cells[1],
                    "symbol": cells[2],
                    "score": float(cells[3]),
                })
            except (ValueError, IndexError):
                continue

        if len(results) >= limit:
            break

    return results


def _parse_composition_table(content: str) -> list[dict]:
    """
    מנתח טבלת הרכב קרן סופי

    Format: | שם חברה | סימול | סוג | משקל | ציון | מחיר נוכחי | מספר מניות ליחידת קרן |
    """
    results = []

    idx = content.find("## הרכב קרן סופי")
    if idx == -1:
        return results

    section_text = content[idx:]
    lines = section_text.split("\n")

    in_table = False
    for line in lines[1:]:
        line = line.strip()

        if line.startswith("| שם חברה"):
            in_table = True
            continue

        if line.startswith("|---") or line.startswith("| ---"):
            continue

        if in_table and (not line.startswith("|") or line.startswith("##")):
            break

        if not in_table or not line.startswith("|"):
            continue

        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]

        if len(cells) >= 7:
            try:
                weight_str = cells[3].replace("%", "").strip()
                results.append({
                    "name": cells[0],
                    "symbol": cells[1],
                    "type": cells[2],
                    "weight": float(weight_str) / 100.0,
                    "score": float(cells[4]),
                    "price": float(cells[5]),
                    "shares": int(cells[6]),
                })
            except (ValueError, IndexError):
                continue

    return results


def find_latest_update_file(base_output_dir: Path, index_name: str) -> Optional[Path]:
    """
    מוצא את קובץ ה-Update.md האחרון למדד נתון

    Args:
        base_output_dir: תיקיית Fund_Docs
        index_name: שם המדד (SP500 או TASE125)

    Returns:
        Optional[Path]: נתיב לקובץ Update.md, או None
    """
    latest_dir = find_latest_fund_dir(base_output_dir, index_name)
    if latest_dir is None:
        return None

    # Look for *_Update.md in the latest quarter folder
    update_files = list(latest_dir.glob("*_Update.md"))
    if not update_files:
        return None

    # Should be exactly one, but take the first
    return update_files[0]
