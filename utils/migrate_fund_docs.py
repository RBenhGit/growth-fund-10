"""
סקריפט מיגרציה למבנה תיקיות חדש של Fund_Docs

מעביר קבצים ממבנה שטוח:
    Fund_Docs/Fund_10_SP500_Q1_2026.md

למבנה היררכי:
    Fund_Docs/SP500/Q1_2026/Fund_10_SP500_Q1_2026.md

שימוש:
    python utils/migrate_fund_docs.py              # תצוגה מקדימה בלבד
    python utils/migrate_fund_docs.py --execute     # ביצוע בפועל
"""

import codecs
import re
import shutil
import sys
from pathlib import Path

# Windows console encoding fix
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def classify_file(filename: str) -> dict | None:
    """
    מסווג קובץ לפי שם ומחזיר מטה-דאטה

    Returns:
        dict with index, quarter, year, or None if not a fund file
    """
    # Pattern: Fund_10_{INDEX}_{Q}_{YEAR}[_suffix].md
    match = re.match(
        r"Fund_10_(SP500|TASE125)_(Q[1-4])_(\d{4})(.*)\.(md|png)$",
        filename
    )
    if match:
        return {
            "index": match.group(1),
            "quarter": match.group(2),
            "year": match.group(3),
            "suffix": match.group(4),
            "ext": match.group(5),
        }
    return None


def plan_migration(fund_docs_dir: Path) -> list[dict]:
    """
    מתכנן את המיגרציה — מחזיר רשימת פעולות

    Returns:
        list of {"source": Path, "dest": Path, "action": str}
    """
    actions = []

    for item in sorted(fund_docs_dir.iterdir()):
        if item.is_dir():
            # Skip existing subdirectories (Gemini, etc.)
            continue

        info = classify_file(item.name)

        if info:
            # Fund file → move to index/quarter subfolder
            dest_dir = fund_docs_dir / info["index"] / f"{info['quarter']}_{info['year']}"
            dest = dest_dir / item.name
            actions.append({
                "source": item,
                "dest": dest,
                "action": "move",
                "dest_dir": dest_dir,
            })
        elif item.name.endswith("_Functionality_Report.md"):
            # Reports → move to Reports subfolder
            dest_dir = fund_docs_dir / "Reports"
            dest = dest_dir / item.name
            actions.append({
                "source": item,
                "dest": dest,
                "action": "move",
                "dest_dir": dest_dir,
            })
        elif item.suffix == ".png":
            # Backtest chart PNGs — try to classify, otherwise move to Reports
            info_png = classify_file(item.name)
            if info_png:
                dest_dir = fund_docs_dir / info_png["index"] / f"{info_png['quarter']}_{info_png['year']}"
                dest = dest_dir / item.name
            else:
                dest_dir = fund_docs_dir / "Reports"
                dest = dest_dir / item.name
            actions.append({
                "source": item,
                "dest": dest,
                "action": "move",
                "dest_dir": dest_dir,
            })
        # else: skip unknown files (CHANGELOG.md, etc.)

    return actions


def execute_migration(actions: list[dict], dry_run: bool = True) -> None:
    """
    מבצע את המיגרציה

    Args:
        actions: רשימת פעולות מ-plan_migration
        dry_run: True = תצוגה מקדימה בלבד
    """
    if not actions:
        print("No files to migrate.")
        return

    # Collect unique directories to create
    dirs_to_create = sorted(set(a["dest_dir"] for a in actions))

    print(f"\n{'=== DRY RUN ===' if dry_run else '=== EXECUTING MIGRATION ==='}\n")
    print(f"Directories to create: {len(dirs_to_create)}")
    for d in dirs_to_create:
        print(f"  mkdir {d.relative_to(d.parent.parent.parent)}")
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)

    print(f"\nFiles to move: {len(actions)}")
    for a in actions:
        src_rel = a["source"].name
        dest_rel = a["dest"].relative_to(a["dest"].parent.parent.parent.parent)
        print(f"  {src_rel} → {dest_rel}")
        if not dry_run:
            shutil.move(str(a["source"]), str(a["dest"]))

    if dry_run:
        print(f"\n(Dry run — no files were moved. Use --execute to apply.)")
    else:
        print(f"\nMigration complete. {len(actions)} files moved.")


def main():
    from config.settings import settings

    fund_docs_dir = settings.OUTPUT_DIR
    print(f"Fund_Docs directory: {fund_docs_dir}")

    if not fund_docs_dir.exists():
        print("Fund_Docs directory does not exist.")
        return

    actions = plan_migration(fund_docs_dir)
    dry_run = "--execute" not in sys.argv

    execute_migration(actions, dry_run=dry_run)


if __name__ == "__main__":
    main()
