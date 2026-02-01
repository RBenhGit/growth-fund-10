#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
מערכת בניית קרן צמיחה 10
סקריפט ראשי להרצת תהליך בניית הקרן

Usage:
    python build_fund.py --index TASE125
    python build_fund.py --index SP500 --quarter Q4 --year 2025
    python build_fund.py --index SP500 --no-cache
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

# הוספת התיקייה הנוכחית ל-path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import settings
from utils.date_utils import get_quarter_and_year, format_fund_name, get_current_date_string

logger = logging.getLogger(__name__)

# יצירת console עבור פלט יפה
console = Console()


def parse_arguments():
    """פרסור ארגומנטים משורת הפקודה"""
    parser = argparse.ArgumentParser(
        description="מערכת בניית קרן צמיחה 10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
דוגמאות שימוש:
  python build_fund.py --index TASE125
  python build_fund.py --index SP500 --quarter Q4 --year 2025
  python build_fund.py --index SP500 --no-cache
        """
    )

    parser.add_argument(
        "--index",
        type=str,
        required=True,
        choices=["TASE125", "SP500"],
        help="שם המדד (TASE125 או SP500)"
    )

    parser.add_argument(
        "--quarter",
        type=str,
        choices=["Q1", "Q2", "Q3", "Q4"],
        help="רבעון (Q1-Q4). אם לא צוין - יחושב אוטומטית"
    )

    parser.add_argument(
        "--year",
        type=int,
        help="שנה. אם לא צוינה - תיקח השנה הנוכחית"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="כפה רענון נתונים (התעלם מ-cache)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="מצב debug (פלט מפורט)"
    )

    return parser.parse_args()


def validate_settings():
    """בדיקת תקינות הגדרות"""
    try:
        settings.validate()
        return True
    except ValueError as e:
        console.print(f"[red]שגיאה בהגדרות:[/red] {e}")
        console.print("[yellow]אנא בדוק את קובץ .env[/yellow]")
        return False


def save_stock_to_cache(stock, cache_dir):
    """
    שמירת מניה ל-cache

    Args:
        stock: אובייקט Stock לשמירה
        cache_dir: תיקיית cache
    """
    import json

    stock_cache = cache_dir / f"{stock.symbol.replace('.', '_')}.json"

    try:
        # Log what we're about to save
        logger.debug(f"Saving {stock.symbol}: base_score={stock.base_score}, potential_score={stock.potential_score}")

        data = stock.model_dump()

        # Verify scores are in the data
        if stock.base_score is not None and data.get('base_score') is None:
            logger.error(f"BUG: {stock.symbol} has base_score={stock.base_score} but model_dump() returned null!")
        if stock.potential_score is not None and data.get('potential_score') is None:
            logger.error(f"BUG: {stock.symbol} has potential_score={stock.potential_score} but model_dump() returned null!")

        with open(stock_cache, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"✓ Successfully wrote {stock_cache.name} ({stock_cache.stat().st_size} bytes)")

    except Exception as e:
        logger.error(f"Failed to save {stock.symbol} to cache: {e}")
        raise


def get_base_company_name(stock):
    """
    חילוץ שם החברה הבסיסי מתוך שם החברה או סימול

    מסיר סיומות כגון: Class A, Class B, Class C, Inc, Ltd, Corp, וכו'
    כדי לזהות חברות עם מספר סוגי מניות.

    Args:
        stock: מניה

    Returns:
        str: שם בסיסי של החברה
    """
    import re

    name = stock.name.upper()
    symbol = stock.symbol.upper()

    # הסרת סיומות נפוצות מהשם
    patterns_to_remove = [
        r'\s+CLASS\s+[ABC]',  # Class A, Class B, Class C
        r'\s+SERIES\s+[ABC]',  # Series A, Series B, Series C
        r'\s+INC\.?$',  # Inc, Inc.
        r'\s+LTD\.?$',  # Ltd, Ltd.
        r'\s+CORP\.?$',  # Corp, Corp.
        r'\s+PLC\.?$',  # PLC, PLC.
        r'\s+LP\.?$',  # LP, LP.
        r'\s+LLC\.?$',  # LLC, LLC.
        r'\s+SA\.?$',  # SA, SA.
        r'\s+AG\.?$',  # AG, AG.
        r'\s+NV\.?$',  # NV, NV.
        r'\s+\(.*\)$',  # (Class A), (NYSE), etc.
    ]

    base_name = name
    for pattern in patterns_to_remove:
        base_name = re.sub(pattern, '', base_name)

    base_name = base_name.strip()

    # אם השם הבסיסי ריק, השתמש בסימול (בלי סיומת)
    if not base_name:
        base_name = symbol.split('.')[0]

    return base_name


def select_stocks_skip_duplicates(ranked_stocks, count):
    """
    בחירת מניות תוך דילוג על כפילויות של חברות

    חברות עם מספר סוגי מניות (Class A, Class B, וכו') נחשבות כחברה אחת.
    אם מספר מניות של אותה חברה ברשימה, נבחר רק את הראשונה שמופיעה (בדירוג הגבוה ביותר).

    דוגמאות לכפילויות שיזוהו:
    - Alphabet: GOOGL (Class A), GOOG (Class C)
    - Fox Corp: FOXA (Class A), FOX (Class B)
    - Berkshire Hathaway: BRK.A (Class A), BRK.B (Class B)

    Args:
        ranked_stocks: רשימת מניות ממוינות לפי דירוג (גבוה לנמוך)
        count: מספר מניות לבחור

    Returns:
        List[Stock]: רשימת מניות נבחרות (ללא כפילויות)
    """
    selected = []
    seen_companies = set()

    for stock in ranked_stocks:
        # קבל שם בסיסי של החברה
        base_name = get_base_company_name(stock)

        # אם כבר יש לנו מניה מחברה זו, דלג
        if base_name in seen_companies:
            continue

        # הוסף את המניה
        selected.append(stock)
        seen_companies.add(base_name)

        # אם הגענו למספר הנדרש, עצור
        if len(selected) >= count:
            break

    return selected


def build_fund(index_name: str, quarter: str, year: int, use_cache: bool):
    """
    תהליך בניית הקרן - 14 שלבים

    Args:
        index_name: שם המדד (TASE125/SP500)
        quarter: רבעון (Q1-Q4)
        year: שנה
        use_cache: האם להשתמש ב-cache
    """
    import json
    import os
    from pathlib import Path
    from data_sources.router import DataSourceRouter
    from data_sources.adapter import DataSourceAdapter
    from data_sources.exceptions import (
        DataSourceError,
        DataSourceConnectionError,
        DataSourceAuthenticationError,
        DataSourceRateLimitError,
        DataSourceNotFoundError
    )
    from models import Stock, Fund, FundPosition
    from fund_builder import FundBuilder
    from rich.table import Table

    console.print(Panel.fit(
        f"[bold cyan]בונה קרן: {format_fund_name(quarter, year, index_name)}[/bold cyan]",
        border_style="cyan"
    ))

    # יצירת data sources עם ניתוב חכם - מקורות נפרדים לנתונים פיננסיים ומחירים
    router = DataSourceRouter()
    adapter = DataSourceAdapter()

    try:
        financial_source = router.get_financial_source(index_name)
        pricing_source = router.get_pricing_source(index_name)
    except ValueError as e:
        console.print(f"[bold red]❌ שגיאת הגדרה:[/bold red] {e}")
        console.print("\n[yellow]אנא הגדר מפתחות API בקובץ .env[/yellow]")
        sys.exit(1)

    financial_source_name = financial_source.__class__.__name__
    pricing_source_name = pricing_source.__class__.__name__

    # הצגת הגדרות מקורות הנתונים
    console.print(Panel(
        f"[bold cyan]הגדרות מקורות נתונים[/bold cyan]\n\n"
        f"מדד: [yellow]{index_name}[/yellow]\n"
        f"מקור נתונים פיננסיים: [yellow]{financial_source_name}[/yellow]\n"
        f"מקור נתוני מחירים: [yellow]{pricing_source_name}[/yellow]\n"
        f"שימוש ב-cache: [yellow]{'מופעל' if use_cache else 'כבוי'}[/yellow]",
        border_style="cyan"
    ))

    # בדיקת חיבור למקורות נתונים
    console.print("\n[bold cyan]בודק חיבור למקורות נתונים...[/bold cyan]")

    try:
        if not financial_source.login():
            raise DataSourceConnectionError(f"לא ניתן להתחבר למקור נתונים פיננסיים: {financial_source_name}")
        console.print(f"[green]✓ מחובר ל-{financial_source_name} (נתונים פיננסיים)[/green]")
    except DataSourceAuthenticationError as e:
        console.print(f"[bold red]❌ שגיאת אימות:[/bold red] {e}")
        console.print("\n[yellow]אנא בדוק את מפתח ה-API בקובץ .env[/yellow]")
        sys.exit(1)
    except DataSourceConnectionError as e:
        console.print(f"[bold red]❌ שגיאת התחברות:[/bold red] {e}")
        console.print("\n[yellow]אנא בדוק את החיבור לאינטרנט[/yellow]")
        sys.exit(1)
    except DataSourceError as e:
        console.print(f"[bold red]❌ שגיאת מקור נתונים:[/bold red] {e}")
        sys.exit(1)

    # בדיקת חיבור למקור מחירים (רק אם שונה ממקור הנתונים הפיננסיים)
    if pricing_source_name != financial_source_name:
        try:
            if not pricing_source.login():
                raise DataSourceConnectionError(f"לא ניתן להתחבר למקור נתוני מחירים: {pricing_source_name}")
            console.print(f"[green]✓ מחובר ל-{pricing_source_name} (נתוני מחירים)[/green]")
        except DataSourceError as e:
            console.print(f"[yellow]⚠ אזהרה:[/yellow] לא ניתן להתחבר למקור מחירים: {e}")
            console.print(f"[yellow]ממשיך עם מקור הנתונים הפיננסיים בלבד[/yellow]")
            pricing_source = financial_source  # Fallback to financial source

    builder = FundBuilder(index_name)
    fund_name = format_fund_name(quarter, year, index_name)

    # תיקיות cache ופלט
    cache_dir = settings.CACHE_DIR / "stocks_data"
    output_dir = settings.OUTPUT_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        # ===== שלב 1: איסוף רשימת מניות מהמדד =====
        task1 = progress.add_task("[cyan]שלב 1: איסוף רשימת מניות מהמדד...", total=None)
        try:
            constituents_cache = cache_dir.parent / "index_constituents" / f"{index_name}_{quarter}_{year}.json"
            constituents_cache.parent.mkdir(parents=True, exist_ok=True)

            if use_cache and constituents_cache.exists():
                with open(constituents_cache, "r", encoding="utf-8") as f:
                    constituents = json.load(f)
                console.print(f"  [green]✓[/green] נטענו {len(constituents)} מניות מ-cache")
            else:
                constituents = financial_source.get_index_constituents(index_name)
                with open(constituents_cache, "w", encoding="utf-8") as f:
                    json.dump(constituents, f, ensure_ascii=False, indent=2)
                console.print(f"  [green]✓[/green] נמצאו {len(constituents)} מניות במדד")

            progress.update(task1, completed=True)
        except Exception as e:
            progress.update(task1, completed=True)
            raise RuntimeError(f"שלב 1 נכשל: {e}")

        # ===== שלב 2: סינון מניות בסיס =====
        task2 = progress.add_task("[cyan]שלב 2: סינון מניות לקרן הבסיס...", total=None)
        try:
            suffix = ".US" if index_name == "SP500" else ".TA"
            base_eligible = []
            all_loaded_stocks = []

            for constituent in constituents:  # עובר על כל המניות במדד
                symbol = constituent["symbol"]
                if not symbol.endswith(suffix):
                    symbol = f"{symbol}{suffix}"

                stock_cache = cache_dir / f"{symbol.replace('.', '_')}.json"

                try:
                    # טעינה מ-cache או שליפה מהשרת
                    if use_cache and stock_cache.exists():
                        with open(stock_cache, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            stock = Stock(**data)
                    else:
                        # שליפה ממקורות נפרדים - נתונים פיננסיים ומחירים
                        logger.info(
                            f"שולף נתוני {symbol}: "
                            f"פיננסיים מ-{financial_source_name}, "
                            f"מחירים מ-{pricing_source_name}"
                        )

                        # שליפת נתונים פיננסיים
                        try:
                            financial_data = financial_source.get_stock_financials(symbol, years=5)
                        except DataSourceNotFoundError:
                            logger.warning(f"מניה {symbol} לא נמצאה ב-{financial_source_name}, מדלג")
                            continue
                        except DataSourceRateLimitError as e:
                            logger.error(f"הגעת למגבלת קריאות API: {e}")
                            console.print(
                                f"[yellow]⚠ הגעת למגבלת קריאות API של {financial_source_name}[/yellow]\n"
                                "[yellow]שקול להשתמש בנתונים שנשמרו ב-cache או להמתין[/yellow]"
                            )
                            raise

                        # תיקוף נתונים פיננסיים
                        if not adapter.validate_financial_data(financial_data, symbol, financial_source_name):
                            logger.error(f"נתונים פיננסיים לא תקינים עבור {symbol}, מדלג")
                            continue

                        # שליפת נתוני מחירים
                        try:
                            market_data = pricing_source.get_stock_market_data(symbol)
                        except DataSourceNotFoundError:
                            logger.warning(f"נתוני מחירים עבור {symbol} לא נמצאו ב-{pricing_source_name}, מדלג")
                            continue
                        except DataSourceError as e:
                            logger.warning(f"שגיאה בשליפת נתוני מחירים עבור {symbol}: {e}")
                            # ממשיך בלי נתוני מחירים - ייתכן שהמניה תיפסל

                        # תיקוף נתוני שוק
                        if not adapter.validate_market_data(market_data, symbol, pricing_source_name):
                            logger.warning(f"נתוני מחירים חלקיים עבור {symbol} - ציון momentum/valuation עלול להיות לא מדויק")

                        # יצירת אובייקט המניה
                        stock = Stock(
                            symbol=symbol,
                            name=constituent["name"],
                            index=index_name,
                            financial_data=financial_data,
                            market_data=market_data
                        )

                    all_loaded_stocks.append(stock)

                    # בדיקת כשירות ועדכון דגלים
                    stock.is_eligible_for_base = stock.check_base_eligibility()
                    stock.is_eligible_for_potential = stock.check_potential_eligibility()

                    if stock.is_eligible_for_base:
                        base_eligible.append(stock)

                    # שמירה/עדכון cache
                    save_stock_to_cache(stock, cache_dir)

                except Exception as e:
                    if settings.DEBUG_MODE:
                        console.print(f"  [yellow]⚠[/yellow] שגיאה בטעינת {symbol}: {e}")
                    continue

            builder.all_stocks = all_loaded_stocks
            builder.base_candidates = base_eligible
            console.print(f"  [green]✓[/green] נמצאו {len(base_eligible)} מניות כשירות לקרן בסיס")
            progress.update(task2, completed=True)
        except Exception as e:
            progress.update(task2, completed=True)
            raise RuntimeError(f"שלב 2 נכשל: {e}")

        # ===== שלב 3: חישוב וציון מניות הבסיס =====
        task3 = progress.add_task("[cyan]שלב 3: חישוב וציון מניות הבסיס...", total=None)
        try:
            ranked_base = builder.score_and_rank_base_stocks(builder.base_candidates)

            # עדכון cache עם ציונים
            logger.info(f"Step 3: Updating cache for {len(ranked_base)} base stocks...")
            for i, stock in enumerate(ranked_base):
                if settings.DEBUG_MODE and i < 5:  # Log first 5 in debug mode
                    logger.debug(f"  Saving {stock.symbol} with base_score={stock.base_score}")
                save_stock_to_cache(stock, cache_dir)
            logger.info(f"Step 3: Cache update complete for {len(ranked_base)} stocks")

            console.print(f"  [green]✓[/green] דורגו {len(ranked_base)} מניות")
            progress.update(task3, completed=True)
        except Exception as e:
            progress.update(task3, completed=True)
            raise RuntimeError(f"שלב 3 נכשל: {e}")

        # ===== שלב 4: בחירת 6 מניות הבסיס =====
        task4 = progress.add_task("[cyan]שלב 4: בחירת 6 מניות הבסיס...", total=None)
        try:
            # בחירה תוך דילוג על כפילויות של Alphabet
            builder.selected_base = select_stocks_skip_duplicates(ranked_base, 6)
            console.print(f"  [green]✓[/green] נבחרו 6 מניות בסיס")
            progress.update(task4, completed=True)
        except Exception as e:
            progress.update(task4, completed=True)
            raise RuntimeError(f"שלב 4 נכשל: {e}")

        # ===== שלב 5: הכנת רשימה למניות פוטנציאל =====
        task5 = progress.add_task("[cyan]שלב 5: הכנת רשימה למניות פוטנציאל...", total=None)
        try:
            base_symbols = {s.symbol for s in builder.selected_base}
            potential_pool = [s for s in builder.all_stocks if s.symbol not in base_symbols]
            console.print(f"  [green]✓[/green] {len(potential_pool)} מניות זמינות לפוטנציאל")
            progress.update(task5, completed=True)
        except Exception as e:
            progress.update(task5, completed=True)
            raise RuntimeError(f"שלב 5 נכשל: {e}")

        # ===== שלב 6: סינון מניות פוטנציאל =====
        task6 = progress.add_task("[cyan]שלב 6: סינון מניות פוטנציאל...", total=None)
        try:
            potential_eligible = []
            for stock in potential_pool:
                if stock.check_potential_eligibility():
                    potential_eligible.append(stock)
            builder.potential_candidates = potential_eligible
            console.print(f"  [green]✓[/green] נמצאו {len(potential_eligible)} מניות כשירות לפוטנציאל")
            progress.update(task6, completed=True)
        except Exception as e:
            progress.update(task6, completed=True)
            raise RuntimeError(f"שלב 6 נכשל: {e}")

        # ===== שלב 7: חישוב ציון פוטנציאל =====
        task7 = progress.add_task("[cyan]שלב 7: חישוב ציון פוטנציאל...", total=None)
        try:
            index_pe = data_source.get_index_pe_ratio(index_name)
            ranked_potential = builder.score_and_rank_potential_stocks(builder.potential_candidates, index_pe)

            # עדכון cache עם ציונים
            logger.info(f"Step 7: Updating cache for {len(ranked_potential)} potential stocks...")
            for i, stock in enumerate(ranked_potential):
                if settings.DEBUG_MODE and i < 5:  # Log first 5 in debug mode
                    logger.debug(f"  Saving {stock.symbol} with potential_score={stock.potential_score}")
                save_stock_to_cache(stock, cache_dir)
            logger.info(f"Step 7: Cache update complete for {len(ranked_potential)} stocks")

            console.print(f"  [green]✓[/green] דורגו {len(ranked_potential)} מניות פוטנציאל")
            progress.update(task7, completed=True)
        except Exception as e:
            progress.update(task7, completed=True)
            raise RuntimeError(f"שלב 7 נכשל: {e}")

        # ===== שלב 8: בחירת ארבע מניות פוטנציאל =====
        task8 = progress.add_task("[cyan]שלב 8: בחירת ארבע מניות פוטנציאל...", total=None)
        try:
            # בחירה תוך דילוג על כפילויות של Alphabet
            builder.selected_potential = select_stocks_skip_duplicates(ranked_potential, 4)
            console.print(f"  [green]✓[/green] נבחרו 4 מניות פוטנציאל")
            progress.update(task8, completed=True)
        except Exception as e:
            progress.update(task8, completed=True)
            raise RuntimeError(f"שלב 8 נכשל: {e}")

        # ===== שלב 9: הקצאת משקלים =====
        task9 = progress.add_task("[cyan]שלב 9: הקצאת משקלים קבועים...", total=None)
        try:
            all_selected = builder.selected_base + builder.selected_potential
            for i, stock in enumerate(all_selected):
                stock._assigned_weight = settings.FUND_WEIGHTS[i]
            console.print(f"  [green]✓[/green] הוקצו משקלים ל-10 מניות")
            progress.update(task9, completed=True)
        except Exception as e:
            progress.update(task9, completed=True)
            raise RuntimeError(f"שלב 9 נכשל: {e}")

        # ===== שלב 10: חישוב עלות מינימלית ליחידת קרן =====
        task10 = progress.add_task("[cyan]שלב 10: חישוב עלות מינימלית ליחידת קרן...", total=None)
        try:
            positions = [(stock, stock._assigned_weight) for stock in all_selected]
            min_cost, shares_dict = builder.calculate_minimum_fund_cost(positions)
            console.print(f"  [green]✓[/green] עלות מינימלית: {min_cost:,.2f}")
            progress.update(task10, completed=True)
        except Exception as e:
            progress.update(task10, completed=True)
            raise RuntimeError(f"שלב 10 נכשל: {e}")

        # ===== שלב 11: הצגת הקרן הסופית =====
        task11 = progress.add_task("[cyan]שלב 11: יצירת טבלת הקרן...", total=None)
        try:
            fund_positions = []
            for i, stock in enumerate(all_selected):
                position_type = "בסיס" if i < 6 else "פוטנציאל"
                fund_positions.append(FundPosition(
                    stock=stock,
                    weight=stock._assigned_weight,
                    shares_per_unit=shares_dict.get(stock.symbol, 0),
                    position_type=position_type
                ))

            fund = Fund(
                name=fund_name,
                quarter=quarter,
                year=year,
                index=index_name,
                positions=fund_positions,
                minimum_cost=min_cost
            )
            console.print(f"  [green]✓[/green] נוצרה טבלת קרן עם 10 מניות")
            progress.update(task11, completed=True)
        except Exception as e:
            progress.update(task11, completed=True)
            raise RuntimeError(f"שלב 11 נכשל: {e}")

        # ===== שלב 12: יצירת מסמך עדכון קרן =====
        task12 = progress.add_task("[cyan]שלב 12: יצירת מסמך עדכון...", total=None)
        try:
            update_doc_path = output_dir / f"{fund_name}_Update.md"

            # חישוב סטטיסטיקות סינון
            total_stocks = len(constituents)
            num_base_eligible = len(base_eligible)
            num_potential_eligible = len(potential_eligible)
            # מניות שלא עברו אף סינון (לא בסיס ולא פוטנציאל)
            num_rejected = total_stocks - len([
                s for s in all_loaded_stocks
                if s.is_eligible_for_base or s.is_eligible_for_potential
            ])
            pct = lambda n: f"{n / total_stocks * 100:.1f}%" if total_stocks > 0 else "0%"

            stats_table = (
                "## סטטיסטיקות סינון\n\n"
                "| מדד | מספר | אחוז |\n"
                "|-----|------|------|\n"
                f"| סה\"כ מניות במדד | {total_stocks} | 100% |\n"
                f"| כשירות לבסיס | {num_base_eligible} | {pct(num_base_eligible)} |\n"
                f"| כשירות לפוטנציאל | {num_potential_eligible} | {pct(num_potential_eligible)} |\n"
                f"| נדחו (לא עברו סינון) | {num_rejected} | {pct(num_rejected)} |\n"
                "\n"
            )

            with open(update_doc_path, "w", encoding="utf-8") as f:
                f.write(f"# עדכון קרן {fund_name}\n\n")
                f.write(f"תאריך עדכון: {get_current_date_string()}\n\n")
                f.write(stats_table)
                f.write("## מניות בסיס מדורגות\n\n")
                f.write("| דירוג | שם חברה | סימול | ציון |\n")
                f.write("|-------|---------|-------|------|\n")
                for i, stock in enumerate(ranked_base, 1):
                    f.write(f"| {i} | {stock.name} | {stock.symbol} | {stock.base_score:.2f} |\n")
                f.write("\n## מניות פוטנציאל מדורגות\n\n")
                f.write("| דירוג | שם חברה | סימול | ציון |\n")
                f.write("|-------|---------|-------|------|\n")
                for i, stock in enumerate(ranked_potential, 1):
                    f.write(f"| {i} | {stock.name} | {stock.symbol} | {stock.potential_score:.2f} |\n")
                f.write("\n## הרכב קרן סופי\n\n")
                f.write(fund.to_markdown())
            console.print(f"  [green]✓[/green] נוצר מסמך עדכון: {update_doc_path.name}")
            progress.update(task12, completed=True)
        except Exception as e:
            progress.update(task12, completed=True)
            raise RuntimeError(f"שלב 12 נכשל: {e}")

        # ===== שלב 13: יצירת מסמכי קרן סופיים =====
        task13 = progress.add_task("[cyan]שלב 13: יצירת מסמך קרן סופי...", total=None)
        try:
            final_doc_path = output_dir / f"{fund_name}.md"
            with open(final_doc_path, "w", encoding="utf-8") as f:
                f.write(f"# {fund_name}\n\n")
                f.write(f"תאריך יצירה: {get_current_date_string()}\n\n")
                f.write(f"מדד: {index_name}\n\n")
                f.write(stats_table)
                f.write(fund.to_markdown())
                f.write(f"\n**עלות מינימלית ליחידת קרן:** {min_cost:,.2f}\n")
            console.print(f"  [green]✓[/green] נוצר מסמך סופי: {final_doc_path.name}")
            progress.update(task13, completed=True)
        except Exception as e:
            progress.update(task13, completed=True)
            raise RuntimeError(f"שלב 13 נכשל: {e}")

        # ===== שלב 14: ולידציה ואימות =====
        task14 = progress.add_task("[cyan]שלב 14: ולידציה ואימות...", total=None)
        try:
            errors = builder.validate_fund(fund)
            if errors:
                console.print(f"  [red]✗[/red] נמצאו {len(errors)} שגיאות:")
                for error in errors:
                    console.print(f"    - {error}")
                raise RuntimeError("אימות הקרן נכשל")
            else:
                console.print(f"  [green]✓[/green] הקרן עברה את כל בדיקות האימות")
            progress.update(task14, completed=True)
        except Exception as e:
            progress.update(task14, completed=True)
            raise RuntimeError(f"שלב 14 נכשל: {e}")

        # ===== Verification: Check cache was updated with scores =====
        console.print("[cyan]Verifying cache was updated with scores...[/cyan]")
        sample_stocks = []
        if builder.selected_base:
            sample_stocks.append(builder.selected_base[0])
        if builder.selected_potential:
            sample_stocks.append(builder.selected_potential[0])

        cache_verification_passed = True
        for stock in sample_stocks:
            stock_cache = cache_dir / f"{stock.symbol.replace('.', '_')}.json"
            try:
                with open(stock_cache, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)

                memory_base = stock.base_score
                memory_potential = stock.potential_score
                cached_base = cached_data.get('base_score')
                cached_potential = cached_data.get('potential_score')

                # Check if in-memory score matches cached score
                if memory_base is not None and cached_base is None:
                    console.print(f"  [red]✗[/red] WARNING: {stock.symbol} has base_score in memory ({memory_base:.2f}) but not in cache!")
                    logger.warning(f"Cache verification failed for {stock.symbol}: base_score not persisted")
                    cache_verification_passed = False
                elif memory_potential is not None and cached_potential is None:
                    console.print(f"  [red]✗[/red] WARNING: {stock.symbol} has potential_score in memory ({memory_potential:.2f}) but not in cache!")
                    logger.warning(f"Cache verification failed for {stock.symbol}: potential_score not persisted")
                    cache_verification_passed = False
                else:
                    console.print(f"  [green]✓[/green] {stock.symbol} cache verified")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Could not verify cache for {stock.symbol}: {e}")
                logger.warning(f"Cache verification error for {stock.symbol}: {e}")

        if not cache_verification_passed:
            console.print("[yellow]⚠ Cache verification found issues - scores may not be persisted correctly[/yellow]")

    console.print("[green]✓[/green] בניית קרן הושלמה בהצלחה!")
    console.print(f"[yellow]מסמכים נשמרו ב:[/yellow] {output_dir}")


def main():
    """פונקציה ראשית"""
    # פרסור ארגומנטים (צריך להיות לפני הגדרת logging)
    args = parse_arguments()

    # Configure logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )

    # הדפסת כותרת
    console.print()
    console.print(Panel.fit(
        "[bold magenta]מערכת בניית קרן צמיחה 10[/bold magenta]\n"
        "[dim]Growth Fund Builder v1.0[/dim]",
        border_style="magenta"
    ))
    console.print()

    # עדכון הגדרות לפי ארגומנטים
    if args.debug:
        settings.DEBUG_MODE = True
        logger.info("Debug mode enabled")

    use_cache = settings.USE_CACHE and not args.no_cache

    # בדיקת תקינות הגדרות
    if not validate_settings():
        sys.exit(1)

    # חישוב רבעון ושנה
    quarter_arg = args.quarter or settings.FUND_QUARTER
    year_arg = args.year or settings.FUND_YEAR

    try:
        quarter, year = get_quarter_and_year(quarter_arg, year_arg)
    except ValueError as e:
        console.print(f"[red]שגיאה:[/red] {e}")
        sys.exit(1)

    # הצגת פרמטרים
    console.print("[bold]פרמטרים:[/bold]")
    console.print(f"  מדד: [cyan]{args.index}[/cyan]")
    console.print(f"  רבעון: [cyan]{quarter}[/cyan]")
    console.print(f"  שנה: [cyan]{year}[/cyan]")
    console.print(f"  שימוש ב-cache: [cyan]{'כן' if use_cache else 'לא'}[/cyan]")
    console.print(f"  נתונים פיננסיים: [cyan]{settings.FINANCIAL_DATA_SOURCE}[/cyan]")
    console.print(f"  נתוני מחירים: [cyan]{settings.PRICING_DATA_SOURCE}[/cyan]")
    console.print()

    # בניית הקרן
    try:
        build_fund(args.index, quarter, year, use_cache)
    except KeyboardInterrupt:
        console.print("\n[yellow]התהליך בוטל על ידי המשתמש[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]שגיאה:[/red] {e}")
        if settings.DEBUG_MODE:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
