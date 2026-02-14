"""
מנוע עדכון רבעוני לקרן צמיחה 10

עובד על בסיס:
1. קובץ Update.md מהרבעון הקודם (מזהה ~50 מניות לעקוב)
2. קבצי cache קיימים (נתונים היסטוריים שנתיים)
3. נתוני LTM רבעוניים חדשים מ-TwelveData
4. מחירים עדכניים מ-yfinance (חינם)
"""

import logging
from pathlib import Path
from typing import List, Tuple, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from config import settings
from models import Stock, Fund, FundPosition
from fund_builder.builder import FundBuilder
from utils.update_parser import parse_update_file, find_latest_update_file
from utils.cache_loader import load_cached_stocks
from utils.ltm_calculator import calculate_ltm, merge_ltm_into_stock
from utils.date_utils import (
    format_fund_name,
    get_fund_output_dir,
    find_previous_fund_dir,
    get_current_date_string,
)
from data_sources.adapter import DataSourceAdapter as adapter

logger = logging.getLogger(__name__)
console = Console()


class QuarterlyUpdater:
    """מנהל עדכון רבעוני לקרן"""

    def __init__(
        self,
        index_name: str,
        quarter: str,
        year: int,
    ):
        self.index_name = index_name
        self.quarter = quarter
        self.year = year
        self.builder = FundBuilder(index_name)
        self.output_dir = get_fund_output_dir(settings.OUTPUT_DIR, index_name, quarter, year)
        self.cache_dir = settings.CACHE_DIR / "stocks_data"

    def run_update(
        self,
        financial_source,
        pricing_source,
        top_base: int = 30,
        top_potential: int = 20,
        dry_run: bool = False,
    ) -> Tuple[Optional[Fund], dict]:
        """
        מריץ תהליך עדכון רבעוני

        Args:
            financial_source: מקור נתונים פיננסיים (TwelveDataSource)
            pricing_source: מקור נתוני מחירים (yfinance)
            top_base: מספר מניות בסיס עליונות לעקוב
            top_potential: מספר מניות פוטנציאל עליונות לעקוב
            dry_run: תצוגה מקדימה בלבד

        Returns:
            Tuple of (Fund, comparison_data dict) or (None, {}) on failure
        """
        fund_name = format_fund_name(self.quarter, self.year, self.index_name)

        console.print(Panel.fit(
            f"[bold cyan]עדכון רבעוני — {fund_name}[/bold cyan]",
            border_style="cyan"
        ))

        # ===== Step 1: Find and parse previous Update.md =====
        console.print("\n[yellow]שלב 1:[/yellow] טוען נתוני רבעון קודם...")

        update_file = find_latest_update_file(settings.OUTPUT_DIR, self.index_name)
        if update_file is None:
            console.print("[red]לא נמצא קובץ Update.md קודם. יש להריץ בנייה מלאה תחילה.[/red]")
            return None, {}

        prev_data = parse_update_file(update_file, top_base=top_base, top_potential=top_potential)
        console.print(f"  [green]✓[/green] נטען: {update_file.name}")
        console.print(f"    מניות בסיס: {len(prev_data['base_candidates'])}")
        console.print(f"    מניות פוטנציאל: {len(prev_data['potential_candidates'])}")
        console.print(f"    מניות נבחרות: {len(prev_data['selected_stocks'])}")

        # ===== Step 2: Load cached stocks =====
        console.print("\n[yellow]שלב 2:[/yellow] טוען נתונים מ-cache...")

        all_symbols = set()
        for s in prev_data["base_candidates"]:
            all_symbols.add(s["symbol"])
        for s in prev_data["potential_candidates"]:
            all_symbols.add(s["symbol"])

        cached_stocks = load_cached_stocks(list(all_symbols), self.cache_dir)
        console.print(f"  [green]✓[/green] נטענו {len(cached_stocks)}/{len(all_symbols)} מניות מ-cache")

        if len(cached_stocks) < 10:
            console.print("[red]לא מספיק מניות ב-cache. יש להריץ בנייה מלאה.[/red]")
            return None, {}

        # ===== Step 3: Fetch quarterly LTM data =====
        console.print(f"\n[yellow]שלב 3:[/yellow] מושך נתונים רבעוניים עבור {len(cached_stocks)} מניות...")

        updated_stocks = {}
        failed_symbols = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"מעדכן LTM עבור {len(cached_stocks)} מניות...",
                total=len(cached_stocks)
            )

            for symbol, stock in cached_stocks.items():
                try:
                    # Fetch quarterly financials from TwelveData
                    quarterly_data = financial_source.get_quarterly_financials(symbol)

                    # Calculate LTM
                    ltm_data = calculate_ltm(quarterly_data)

                    # Get current pricing from yfinance (free)
                    current_price = None
                    market_cap = None
                    pe_ratio = None
                    try:
                        pricing_symbol = adapter.normalize_symbol(
                            symbol, self.index_name, pricing_source.name
                        )
                        market_data = pricing_source.get_stock_market_data(pricing_symbol)
                        current_price = market_data.current_price
                        market_cap = market_data.market_cap
                        pe_ratio = market_data.pe_ratio
                    except Exception as e:
                        logger.warning(f"Failed to get pricing for {symbol}: {e}")
                        # Fall back to cached pricing
                        if stock.market_data:
                            current_price = stock.market_data.current_price
                            market_cap = stock.market_data.market_cap
                            pe_ratio = stock.market_data.pe_ratio

                    # Merge LTM into stock
                    updated = merge_ltm_into_stock(
                        stock, ltm_data,
                        current_price=current_price,
                        market_cap=market_cap,
                        pe_ratio=pe_ratio,
                    )
                    updated_stocks[symbol] = updated

                except Exception as e:
                    logger.warning(f"Failed to update {symbol}: {e}")
                    failed_symbols.append(symbol)
                    # Keep original cached stock as fallback
                    updated_stocks[symbol] = stock

                progress.advance(task)

        console.print(f"  [green]✓[/green] עודכנו {len(updated_stocks) - len(failed_symbols)}/{len(updated_stocks)} מניות")
        if failed_symbols:
            console.print(f"  [yellow]⚠ נכשלו:[/yellow] {', '.join(failed_symbols[:10])}")

        # ===== Step 4: Re-check eligibility =====
        console.print("\n[yellow]שלב 4:[/yellow] בדיקת כשירות מחדש...")

        base_eligible = []
        potential_eligible = []
        base_symbols_from_prev = {s["symbol"] for s in prev_data["base_candidates"]}

        for symbol, stock in updated_stocks.items():
            stock.check_base_eligibility()
            stock.check_potential_eligibility()

            if stock.is_eligible_for_base and symbol in base_symbols_from_prev:
                base_eligible.append(stock)
            elif stock.is_eligible_for_potential:
                potential_eligible.append(stock)

        console.print(f"  [green]✓[/green] כשירות בסיס: {len(base_eligible)} מניות")
        console.print(f"  [green]✓[/green] כשירות פוטנציאל: {len(potential_eligible)} מניות")

        # ===== Step 5: Re-score and rank =====
        console.print("\n[yellow]שלב 5:[/yellow] ציון ודירוג מחדש...")

        ranked_base = self.builder.score_and_rank_base_stocks(base_eligible)
        console.print(f"  [green]✓[/green] דורגו {len(ranked_base)} מניות בסיס")

        # Calculate index P/E for potential scoring
        pe_values = [s.pe_ratio for s in updated_stocks.values() if s.pe_ratio and s.pe_ratio > 0]
        index_pe = sum(pe_values) / len(pe_values) if pe_values else None

        # Remove base-selected stocks from potential pool
        from build_fund import select_stocks_skip_duplicates
        selected_base = select_stocks_skip_duplicates(ranked_base, 6)
        selected_base_symbols = {s.symbol for s in selected_base}

        potential_pool = [s for s in potential_eligible if s.symbol not in selected_base_symbols]
        ranked_potential = self.builder.score_and_rank_potential_stocks(potential_pool, index_pe)
        console.print(f"  [green]✓[/green] דורגו {len(ranked_potential)} מניות פוטנציאל")

        selected_potential = select_stocks_skip_duplicates(ranked_potential, 4)

        # ===== Step 6: Build fund =====
        console.print("\n[yellow]שלב 6:[/yellow] בניית קרן מעודכנת...")

        weights = settings.FUND_WEIGHTS
        positions = []
        for i, stock in enumerate(selected_base):
            positions.append((stock, weights[i]))
        for i, stock in enumerate(selected_potential):
            positions.append((stock, weights[6 + i]))

        minimum_cost, shares_per_stock = self.builder.calculate_minimum_fund_cost(positions)

        fund = Fund(
            name=fund_name,
            index=self.index_name,
            quarter=self.quarter,
            year=self.year,
            creation_date=get_current_date_string(),
            positions=[],
            minimum_cost=minimum_cost,
        )

        for stock, weight in positions:
            shares = shares_per_stock.get(stock.symbol, 1)
            position_type = "בסיס" if stock in selected_base else "פוטנציאל"
            fund.add_position(stock, weight, shares, position_type)

        # Validate
        errors = self.builder.validate_fund(fund)
        if errors:
            console.print("[yellow]⚠ אזהרות אימות:[/yellow]")
            for error in errors:
                console.print(f"  - {error}")
        else:
            console.print(f"  [green]✓[/green] קרן תקינה — 10 מניות, משקלים = 100%")

        # ===== Step 7: Compare with previous =====
        console.print("\n[yellow]שלב 7:[/yellow] השוואה עם רבעון קודם...")

        comparison = self._compare_with_previous(prev_data, fund)

        console.print(f"  נוספו: {comparison['added_count']}")
        console.print(f"  הוסרו: {comparison['removed_count']}")
        console.print(f"  נשארו: {comparison['retained_count']}")

        if comparison["added"]:
            for s in comparison["added"]:
                console.print(f"    [green]+[/green] {s['symbol']} ({s['type']}, {s['weight']*100:.0f}%)")
        if comparison["removed"]:
            for s in comparison["removed"]:
                console.print(f"    [red]-[/red] {s['symbol']} ({s['type']}, {s['weight']*100:.0f}%)")

        # ===== Step 8: Save outputs =====
        if dry_run:
            console.print("\n[yellow]מצב תצוגה מקדימה (dry-run) — לא נשמרו קבצים[/yellow]")
        else:
            console.print("\n[yellow]שלב 8:[/yellow] שמירת מסמכים...")
            self._save_outputs(fund, ranked_base, ranked_potential, comparison, prev_data)
            console.print(f"  [green]✓[/green] מסמכים נשמרו ב: {self.output_dir}")

        console.print(f"\n[green]✓ עדכון רבעוני הושלם בהצלחה![/green]")
        console.print(f"  עלות מינימלית: {'₪' if self.index_name == 'TASE125' else '$'}{minimum_cost:,.2f}")

        return fund, comparison

    def _compare_with_previous(self, prev_data: dict, new_fund: Fund) -> dict:
        """
        משווה הרכב קרן חדש עם הרבעון הקודם
        """
        prev_symbols = {s["symbol"]: s for s in prev_data["selected_stocks"]}
        new_symbols = {pos.stock.symbol: pos for pos in new_fund.positions}

        added = []
        removed = []
        retained = []
        score_changes = []

        # Stocks added
        for symbol, pos in new_symbols.items():
            if symbol not in prev_symbols:
                added.append({
                    "symbol": symbol,
                    "name": pos.stock.name,
                    "type": pos.position_type,
                    "weight": pos.weight,
                    "score": pos.stock.base_score if pos.position_type == "בסיס" else pos.stock.potential_score,
                })

        # Stocks removed
        for symbol, prev in prev_symbols.items():
            if symbol not in new_symbols:
                removed.append({
                    "symbol": symbol,
                    "name": prev["name"],
                    "type": prev["type"],
                    "weight": prev["weight"],
                    "score": prev["score"],
                })

        # Stocks retained
        for symbol in prev_symbols:
            if symbol in new_symbols:
                pos = new_symbols[symbol]
                prev = prev_symbols[symbol]
                new_score = pos.stock.base_score if pos.position_type == "בסיס" else pos.stock.potential_score
                retained.append({
                    "symbol": symbol,
                    "name": pos.stock.name,
                    "old_weight": prev["weight"],
                    "new_weight": pos.weight,
                    "old_score": prev["score"],
                    "new_score": new_score,
                    "weight_changed": abs(prev["weight"] - pos.weight) > 0.001,
                })

        return {
            "added": added,
            "removed": removed,
            "retained": retained,
            "added_count": len(added),
            "removed_count": len(removed),
            "retained_count": len(retained),
            "previous_fund_name": prev_data["fund_name"],
            "previous_date": prev_data["date"],
        }

    def _save_outputs(self, fund: Fund, ranked_base: list, ranked_potential: list, comparison: dict, prev_data: dict) -> None:
        """
        שמירת כל מסמכי הפלט
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        fund_name = format_fund_name(self.quarter, self.year, self.index_name)

        # 1. Fund document
        fund_path = self.output_dir / f"{fund_name}.md"
        with open(fund_path, "w", encoding="utf-8") as f:
            f.write(f"# {fund_name}\n\n")
            f.write(f"תאריך יצירה: {get_current_date_string()}\n")
            f.write(f"מדד: {self.index_name}\n")
            f.write(f"סוג: עדכון רבעוני (LTM)\n\n")
            f.write(fund.to_markdown())
            f.write(f"\n\nעלות מינימלית ליחידת קרן: {'₪' if self.index_name == 'TASE125' else '$'}{fund.minimum_cost:,.2f}\n")

        # 2. Update document (ranked tables)
        update_path = self.output_dir / f"{fund_name}_Update.md"
        with open(update_path, "w", encoding="utf-8") as f:
            f.write(f"# עדכון קרן {fund_name}\n\n")
            f.write(f"תאריך עדכון: {get_current_date_string()}\n\n")

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

        # 3. Comparison document
        comparison_path = self.output_dir / f"{fund_name}_Comparison.md"
        with open(comparison_path, "w", encoding="utf-8") as f:
            f.write(f"# השוואה רבעונית — {fund_name}\n\n")
            f.write(f"עדכון מ: {comparison['previous_fund_name']} ({comparison['previous_date']})\n")
            f.write(f"עדכון ל: {fund_name} ({get_current_date_string()})\n\n")

            f.write("## סיכום שינויים\n\n")
            f.write(f"- מניות שנוספו: {comparison['added_count']}\n")
            f.write(f"- מניות שהוסרו: {comparison['removed_count']}\n")
            f.write(f"- מניות שנשארו: {comparison['retained_count']}\n\n")

            if comparison["added"]:
                f.write("## מניות חדשות\n\n")
                f.write("| סימול | שם | סוג | משקל | ציון |\n")
                f.write("|-------|-----|-----|------|------|\n")
                for s in comparison["added"]:
                    score = s["score"] or 0
                    f.write(f"| {s['symbol']} | {s['name']} | {s['type']} | {s['weight']*100:.1f}% | {score:.2f} |\n")

            if comparison["removed"]:
                f.write("\n## מניות שהוסרו\n\n")
                f.write("| סימול | שם | סוג | משקל קודם | ציון קודם |\n")
                f.write("|-------|-----|-----|-----------|----------|\n")
                for s in comparison["removed"]:
                    f.write(f"| {s['symbol']} | {s['name']} | {s['type']} | {s['weight']*100:.1f}% | {s['score']:.2f} |\n")

            if comparison["retained"]:
                f.write("\n## מניות שנשארו\n\n")
                f.write("| סימול | שם | משקל קודם | משקל חדש | ציון קודם | ציון חדש | שינוי |\n")
                f.write("|-------|-----|-----------|----------|-----------|---------|-------|\n")
                for s in comparison["retained"]:
                    new_score = s["new_score"] or 0
                    weight_change = "→" if not s["weight_changed"] else ("↑" if s["new_weight"] > s["old_weight"] else "↓")
                    f.write(
                        f"| {s['symbol']} | {s['name']} | "
                        f"{s['old_weight']*100:.1f}% | {s['new_weight']*100:.1f}% | "
                        f"{s['old_score']:.2f} | {new_score:.2f} | {weight_change} |\n"
                    )

        # 4. Save updated cache files
        from build_fund import save_stock_to_cache
        for pos in fund.positions:
            save_stock_to_cache(pos.stock, self.cache_dir)

        # 5. Append to CHANGELOG.md
        from utils.changelog import append_to_changelog
        changelog_path = settings.OUTPUT_DIR / "CHANGELOG.md"
        append_to_changelog(
            comparison=comparison,
            fund_name=fund_name,
            minimum_cost=fund.minimum_cost or 0.0,
            index_name=self.index_name,
            changelog_path=changelog_path,
        )

        logger.info(f"Saved update documents to {self.output_dir}")
