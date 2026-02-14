"""
ניהול CHANGELOG.md — מעקב אחר שינויים בהרכב הקרן לאורך רבעונים
"""

from datetime import datetime
from pathlib import Path


def append_to_changelog(
    comparison: dict,
    fund_name: str,
    minimum_cost: float,
    index_name: str,
    changelog_path: Path,
) -> None:
    """
    מוסיף רשומת עדכון ל-CHANGELOG.md

    Args:
        comparison: dict מ-QuarterlyUpdater._compare_with_previous()
        fund_name: שם הקרן (e.g., Fund_10_SP500_Q2_2026)
        minimum_cost: עלות מינימלית
        index_name: SP500 או TASE125
        changelog_path: נתיב ל-CHANGELOG.md
    """
    currency = "₪" if index_name == "TASE125" else "$"
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Build summary line
    if comparison["added_count"] == 0 and comparison["removed_count"] == 0:
        summary = "ללא שינויי הרכב"
    else:
        parts = []
        if comparison["added_count"] > 0:
            parts.append(f"{comparison['added_count']} מניות נוספו")
        if comparison["removed_count"] > 0:
            parts.append(f"{comparison['removed_count']} מניות הוסרו")
        summary = ", ".join(parts)

    lines = []
    lines.append(f"### [{date_str}] {fund_name} — {summary}")
    lines.append("")
    lines.append(f"**עדכון מ:** {comparison['previous_fund_name']} ({comparison['previous_date']})")
    lines.append("")

    if comparison["added"]:
        for s in comparison["added"]:
            score = s["score"] or 0
            lines.append(f"- **+** {s['name']} ({s['symbol']}) — {s['type']}, {s['weight']*100:.0f}%, ציון {score:.2f}")

    if comparison["removed"]:
        for s in comparison["removed"]:
            lines.append(f"- **-** {s['name']} ({s['symbol']}) — {s['type']}, {s['weight']*100:.0f}%")

    if not comparison["added"] and not comparison["removed"]:
        lines.append("- ללא שינויים בהרכב")

    lines.append("")
    lines.append(f"**עלות מינימלית:** {currency}{minimum_cost:,.2f}")
    lines.append("")
    lines.append("---")
    lines.append("")

    entry_text = "\n".join(lines)

    # Read or create changelog
    if changelog_path.exists():
        content = changelog_path.read_text(encoding="utf-8")
    else:
        content = "# Growth Fund 10 — Changelog\n\nמעקב אחר שינויי הרכב הקרן לאורך רבעונים.\n\n---\n\n"

    # Append at end (chronological order — newest at bottom)
    content += entry_text

    changelog_path.write_text(content, encoding="utf-8")
