#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
בדיקה מקיפה של כל מקורות הנתונים
Comprehensive test of all data sources

Tests that all data sources:
1. Implement the BaseDataSource interface correctly
2. Have the get_stock_data() method
3. Return valid FinancialData and MarketData
4. Work with the router system
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import settings
from data_sources.router import DataSourceRouter
from data_sources.adapter import DataSourceAdapter
from data_sources import (
    EODHDDataSource,
    FMPDataSource,
    TASEDataHubSource,
    AlphaVantageSource,
    YFinanceSource
)

console = Console()


def test_source(source_class, source_name: str, test_symbol: str, index_name: str) -> dict:
    """
    בדיקת מקור נתונים בודד
    Test a single data source

    Args:
        source_class: מחלקת מקור הנתונים / Data source class
        source_name: שם המקור / Source name
        test_symbol: סימול לבדיקה / Test symbol
        index_name: שם המדד / Index name

    Returns:
        dict: תוצאות הבדיקה / Test results
    """
    console.print(f"\n[bold cyan]בודק {source_name}...[/bold cyan]")

    results = {
        "source": source_name,
        "login": False,
        "get_constituents": False,
        "get_stock_data": False,
        "get_financials": False,
        "get_market": False,
        "get_index_pe": False,
        "data_valid": False,
        "error": None
    }

    try:
        source = source_class()

        # Test 1: Login
        if not source.login():
            results["error"] = "התחברות נכשלה / Login failed"
            console.print(f"[red]❌ התחברות נכשלה[/red]")
            return results
        results["login"] = True
        console.print(f"[green]✓ התחברות הצליחה[/green]")

        # Test 2: Get index constituents
        try:
            constituents = source.get_index_constituents(index_name)
            if constituents and len(constituents) > 0:
                results["get_constituents"] = True
                console.print(f"[green]✓ נמצאו {len(constituents)} רכיבי מדד[/green]")
            else:
                console.print(f"[yellow]⚠ רשימת רכיבים ריקה[/yellow]")
        except NotImplementedError:
            console.print(f"[yellow]⚠ get_index_constituents לא מומש[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ שגיאה בשליפת רכיבי מדד: {e}[/red]")

        # Test 3: Get stock data (unified method)
        try:
            financial_data, market_data = source.get_stock_data(test_symbol, years=5)
            results["get_stock_data"] = True
            console.print(f"[green]✓ get_stock_data() עובד[/green]")

            # Validate returned data
            adapter = DataSourceAdapter()
            financial_valid = adapter.validate_financial_data(financial_data, test_symbol, source_name)
            market_valid = adapter.validate_market_data(market_data, test_symbol, source_name)

            if financial_valid and market_valid:
                results["data_valid"] = True
                console.print(f"[green]✓ נתונים תקינים[/green]")
                console.print(f"   שווי שוק: ${financial_data.market_cap:,.0f}")
                console.print(f"   מחיר: ${financial_data.current_price:.2f}")
                console.print(f"   שנות הכנסה: {sorted(financial_data.revenues.keys())}")
            else:
                console.print(f"[yellow]⚠ נתונים חלקיים או לא תקינים[/yellow]")

        except Exception as e:
            results["error"] = str(e)
            console.print(f"[red]❌ שגיאה ב-get_stock_data(): {e}[/red]")

        # Test 4: Get stock financials (separate method)
        try:
            financial_data = source.get_stock_financials(test_symbol, years=5)
            results["get_financials"] = True
            console.print(f"[green]✓ get_stock_financials() עובד[/green]")
        except Exception as e:
            console.print(f"[red]❌ שגיאה ב-get_stock_financials(): {e}[/red]")

        # Test 5: Get market data (separate method)
        try:
            market_data = source.get_stock_market_data(test_symbol)
            results["get_market"] = True
            console.print(f"[green]✓ get_stock_market_data() עובד[/green]")
        except Exception as e:
            console.print(f"[red]❌ שגיאה ב-get_stock_market_data(): {e}[/red]")

        # Test 6: Get index P/E ratio
        try:
            pe = source.get_index_pe_ratio(index_name)
            results["get_index_pe"] = True
            if pe:
                console.print(f"[green]✓ P/E של מדד: {pe:.2f}[/green]")
            else:
                console.print(f"[yellow]⚠ P/E של מדד לא זמין[/yellow]")
        except NotImplementedError:
            console.print(f"[yellow]⚠ get_index_pe_ratio לא מומש[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ שגיאה בשליפת P/E: {e}[/red]")

        source.logout()
        return results

    except Exception as e:
        results["error"] = str(e)
        console.print(f"[red]❌ שגיאה כללית: {e}[/red]")
        return results


def test_router(index_name: str):
    """
    בדיקת מערכת הניתוב (Router)
    Test the routing system

    Args:
        index_name: שם המדד / Index name
    """
    console.print(f"\n[bold cyan]בודק Router עבור {index_name}...[/bold cyan]")

    try:
        router = DataSourceRouter()

        # Test financial source selection
        financial_source = router.get_financial_source(index_name)
        console.print(f"[green]✓ נבחר מקור פיננסי: {financial_source.__class__.__name__}[/green]")

        # Test pricing source selection
        pricing_source = router.get_pricing_source(index_name)
        console.print(f"[green]✓ נבחר מקור מחירים: {pricing_source.__class__.__name__}[/green]")

        # Test legacy method (backwards compatibility)
        legacy_source = router.get_data_source(index_name)
        console.print(f"[green]✓ מתודה ישנה (legacy) עובדת: {legacy_source.__class__.__name__}[/green]")

        return True
    except Exception as e:
        console.print(f"[red]❌ שגיאה ב-Router: {e}[/red]")
        return False


def main():
    """
    בודק את כל מקורות הנתונים הזמינים
    Test all available data sources
    """
    console.print(Panel.fit(
        "[bold]בדיקה מקיפה של מקורות נתונים[/bold]\n"
        "Comprehensive Data Source Test\n\n"
        "בודק: ממשק, get_stock_data(), תיקוף נתונים, router",
        border_style="cyan"
    ))

    # Test configurations: (name, class, test_symbol, index_name)
    tests = []

    if settings.EODHD_API_KEY:
        tests.append(("EODHD (US)", EODHDDataSource, "AAPL.US", "SP500"))
        tests.append(("EODHD (TASE)", EODHDDataSource, "LPSN.TA", "TASE125"))

    if settings.FMP_API_KEY:
        tests.append(("FMP", FMPDataSource, "AAPL", "SP500"))

    if settings.TASE_DATA_HUB_API_KEY:
        tests.append(("TASE Data Hub", TASEDataHubSource, "LPSN.TA", "TASE125"))

    if settings.ALPHAVANTAGE_API_KEY:
        tests.append(("Alpha Vantage", AlphaVantageSource, "AAPL", "SP500"))

    # YFinance doesn't need API key
    tests.append(("YFinance (US)", YFinanceSource, "AAPL", "SP500"))
    tests.append(("YFinance (TASE)", YFinanceSource, "LPSN.TA", "TASE125"))

    if not tests:
        console.print("[red]לא הוגדרו מפתחות API. אנא הגדר קובץ .env[/red]")
        console.print("[yellow]No API keys configured. Please set up .env file.[/yellow]")
        return

    # Run tests
    results = []
    for name, source_class, symbol, index in tests:
        result = test_source(source_class, name, symbol, index)
        results.append(result)

    # Test router system
    console.print("\n" + "="*60)
    router_us_ok = test_router("SP500")
    router_tase_ok = test_router("TASE125")

    # Summary table
    console.print("\n[bold]סיכום תוצאות / Test Summary:[/bold]\n")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("מקור / Source")
    table.add_column("התחברות / Login")
    table.add_column("get_stock_data()")
    table.add_column("נתונים תקינים / Valid Data")
    table.add_column("סטטוס / Status")

    for result in results:
        login_status = "[green]✓[/green]" if result["login"] else "[red]❌[/red]"
        stock_data_status = "[green]✓[/green]" if result["get_stock_data"] else "[red]❌[/red]"
        data_valid_status = "[green]✓[/green]" if result["data_valid"] else "[yellow]⚠[/yellow]"

        if result["login"] and result["get_stock_data"] and result["data_valid"]:
            overall_status = "[green]תקין / PASS[/green]"
        elif result["login"] and result["get_stock_data"]:
            overall_status = "[yellow]חלקי / PARTIAL[/yellow]"
        else:
            overall_status = "[red]נכשל / FAIL[/red]"

        table.add_row(
            result["source"],
            login_status,
            stock_data_status,
            data_valid_status,
            overall_status
        )

    console.print(table)

    # Router summary
    console.print(f"\n[bold]Router:[/bold]")
    console.print(f"  SP500: {'[green]✓ תקין[/green]' if router_us_ok else '[red]❌ נכשל[/red]'}")
    console.print(f"  TASE125: {'[green]✓ תקין[/green]' if router_tase_ok else '[red]❌ נכשל[/red]'}")

    # Final summary
    passed = sum(1 for r in results if r["login"] and r["get_stock_data"] and r["data_valid"])
    total = len(results)

    console.print(f"\n[bold]סיכום סופי / Final Summary:[/bold]")
    console.print(f"  עברו: {passed}/{total} מקורות")
    console.print(f"  Passed: {passed}/{total} sources")

    if passed == total and router_us_ok and router_tase_ok:
        console.print("\n[bold green]✓ כל הבדיקות עברו בהצלחה![/bold green]")
        console.print("[bold green]✓ All tests passed successfully![/bold green]")
    else:
        console.print("\n[bold yellow]⚠ חלק מהבדיקות נכשלו[/bold yellow]")
        console.print("[bold yellow]⚠ Some tests failed[/bold yellow]")


if __name__ == "__main__":
    main()
