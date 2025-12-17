#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QA Test: בדיקת אינטגרציה של מקורות נתונים
בודק שילוב של EODHD (נתונים פיננסיים) + yfinance (מחירים)
"""

import sys
from pathlib import Path
import requests

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from config import settings

console = Console()

# Test stocks
TEST_STOCKS_US = ["AAPL.US", "MSFT.US", "GOOGL.US"]
TEST_STOCKS_TASE = ["TEVA.TA", "NICE.TA"]


def test_eodhd_financial_data(symbol: str):
    """
    בדיקת נתונים פיננסיים מ-EODHD

    Args:
        symbol: סימול המניה (לדוגמה: AAPL.US, TEVA.TA)

    Returns:
        dict: נתונים פיננסיים או None אם נכשל
    """
    if not settings.EODHD_API_KEY:
        console.print("[red]✗[/red] חסר EODHD_API_KEY")
        return None

    base_url = "https://eodhd.com/api"
    url = f"{base_url}/fundamentals/{symbol}"
    params = {
        "api_token": settings.EODHD_API_KEY,
        "fmt": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] {symbol}: HTTP {response.status_code}")
            return None

        data = response.json()

        # חילוץ נתונים חשובים
        general = data.get("General", {})
        highlights = data.get("Highlights", {})
        financials = data.get("Financials", {})
        income_statements = financials.get("Income_Statement", {}).get("yearly", {})

        result = {
            "symbol": symbol,
            "name": general.get("Name", "N/A"),
            "sector": general.get("Sector", "N/A"),
            "market_cap": highlights.get("MarketCapitalization", 0),
            "pe_ratio": highlights.get("PERatio", 0),
            "income_statements_count": len(income_statements),
            "latest_revenue": None,
            "latest_net_income": None
        }

        # נתונים מהדוח האחרון
        if income_statements:
            latest_year = max(income_statements.keys())
            latest = income_statements[latest_year]
            result["latest_revenue"] = float(latest.get("totalRevenue", 0))
            result["latest_net_income"] = float(latest.get("netIncome", 0))
            result["latest_year"] = latest_year

        return result

    except Exception as e:
        console.print(f"[red]✗[/red] {symbol}: {e}")
        return None


def test_yfinance_pricing_data(symbol: str):
    """
    בדיקת נתוני מחירים מ-yfinance

    Args:
        symbol: סימול המניה (ללא סיומת - לדוגמה: AAPL, TEVA.TA)

    Returns:
        dict: נתוני מחירים או None אם נכשל
    """
    try:
        import yfinance as yf

        # המרת סימול: AAPL.US -> AAPL, TEVA.TA -> TEVA.TA (נשאר כמו שהוא)
        yf_symbol = symbol.replace(".US", "")

        ticker = yf.Ticker(yf_symbol)

        # שליפת נתונים היסטוריים (שנה אחרונה)
        hist = ticker.history(period="1y")

        if hist.empty:
            console.print(f"[red]✗[/red] {symbol}: אין נתוני מחירים")
            return None

        # חישוב סטטיסטיקות
        current_price = hist['Close'].iloc[-1]
        high_52w = hist['High'].max()
        low_52w = hist['Low'].min()
        avg_volume = hist['Volume'].mean()

        result = {
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "current_price": current_price,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "avg_volume": avg_volume,
            "data_points": len(hist),
            "date_range": f"{hist.index[0].date()} to {hist.index[-1].date()}"
        }

        return result

    except ImportError:
        console.print("[red]✗[/red] yfinance לא מותקן - הרץ: pip install yfinance")
        return None
    except Exception as e:
        console.print(f"[red]✗[/red] {symbol}: {e}")
        return None


def run_qa_test():
    """הרצת בדיקת QA מלאה"""
    console.print(Panel.fit(
        "[bold cyan]QA Test: בדיקת אינטגרציה של מקורות נתונים[/bold cyan]\n"
        "[dim]EODHD (Financial) + yfinance (Pricing)[/dim]",
        border_style="cyan"
    ))
    console.print()

    # הצגת קונפיגורציה
    console.print("[bold]הגדרות נוכחיות:[/bold]")
    console.print(f"  נתונים פיננסיים: [cyan]{settings.FINANCIAL_DATA_SOURCE}[/cyan]")
    console.print(f"  נתוני מחירים: [cyan]{settings.PRICING_DATA_SOURCE}[/cyan]")
    console.print(f"  EODHD API Key: [yellow]{settings.EODHD_API_KEY[:10] if settings.EODHD_API_KEY else 'לא מוגדר'}...[/yellow]")
    console.print()

    all_tests_passed = True

    # ========== בדיקה 1: מניות אמריקאיות ==========
    console.print(Panel.fit("[bold magenta]בדיקה 1: מניות אמריקאיות (S&P500)[/bold magenta]"))
    console.print()

    us_results = []
    for symbol in TEST_STOCKS_US:
        console.print(f"[cyan]בודק {symbol}...[/cyan]")

        # נתונים פיננסיים מ-EODHD
        financial = test_eodhd_financial_data(symbol)
        if not financial:
            all_tests_passed = False
            console.print(f"[red]✗[/red] נכשל לטעון נתונים פיננסיים עבור {symbol}")
            continue

        console.print(f"  [green]✓[/green] EODHD: {financial['name']}")
        console.print(f"    • Market Cap: ${financial['market_cap']/1e9:.2f}B")
        console.print(f"    • Sector: {financial['sector']}")
        console.print(f"    • Income Statements: {financial['income_statements_count']} years")

        # נתוני מחירים מ-yfinance
        pricing = test_yfinance_pricing_data(symbol)
        if not pricing:
            all_tests_passed = False
            console.print(f"[red]✗[/red] נכשל לטעון נתוני מחירים עבור {symbol}")
            continue

        console.print(f"  [green]✓[/green] yfinance: ${pricing['current_price']:.2f}")
        console.print(f"    • 52W Range: ${pricing['low_52w']:.2f} - ${pricing['high_52w']:.2f}")
        console.print(f"    • Avg Volume: {pricing['avg_volume']:,.0f}")
        console.print(f"    • Data Points: {pricing['data_points']} days")

        us_results.append({
            "symbol": symbol,
            "financial": financial,
            "pricing": pricing
        })
        console.print()

    # ========== בדיקה 2: מניות ישראליות ==========
    console.print(Panel.fit("[bold magenta]בדיקה 2: מניות ישראליות (TASE)[/bold magenta]"))
    console.print()

    tase_results = []
    for symbol in TEST_STOCKS_TASE:
        console.print(f"[cyan]בודק {symbol}...[/cyan]")

        # נתונים פיננסיים מ-EODHD
        financial = test_eodhd_financial_data(symbol)
        if not financial:
            console.print(f"[yellow]⚠[/yellow] EODHD: נתוני TASE עשויים לדרוש מנוי מתקדם")
        else:
            console.print(f"  [green]✓[/green] EODHD: {financial['name']}")
            console.print(f"    • Income Statements: {financial['income_statements_count']} years")

        # נתוני מחירים מ-yfinance
        pricing = test_yfinance_pricing_data(symbol)
        if not pricing:
            console.print(f"[yellow]⚠[/yellow] yfinance: ייתכן ובעיה עם מניות TASE")
        else:
            console.print(f"  [green]✓[/green] yfinance: ₪{pricing['current_price']:.2f}")
            console.print(f"    • Data Points: {pricing['data_points']} days")

        if financial or pricing:
            tase_results.append({
                "symbol": symbol,
                "financial": financial,
                "pricing": pricing
            })
        console.print()

    # ========== סיכום ==========
    console.print(Panel.fit("[bold green]סיכום בדיקות[/bold green]"))
    console.print()

    # טבלת תוצאות
    table = Table(title="תוצאות QA")
    table.add_column("מניה", style="cyan")
    table.add_column("EODHD\n(Financial)", justify="center")
    table.add_column("yfinance\n(Pricing)", justify="center")
    table.add_column("סטטוס כללי", justify="center")

    for result in us_results + tase_results:
        symbol = result['symbol']
        eodhd_ok = "✓" if result['financial'] else "✗"
        yfinance_ok = "✓" if result['pricing'] else "✗"

        eodhd_style = "green" if result['financial'] else "red"
        yfinance_style = "green" if result['pricing'] else "red"

        # סטטוס כללי
        if result['financial'] and result['pricing']:
            status = "[green]✓ הצלחה[/green]"
        elif result['financial'] or result['pricing']:
            status = "[yellow]⚠ חלקי[/yellow]"
        else:
            status = "[red]✗ כשלון[/red]"

        table.add_row(
            symbol,
            f"[{eodhd_style}]{eodhd_ok}[/{eodhd_style}]",
            f"[{yfinance_style}]{yfinance_ok}[/{yfinance_style}]",
            status
        )

    console.print(table)
    console.print()

    # סיכום סופי
    total_tests = len(us_results) + len(tase_results)
    successful_financial = sum(1 for r in us_results + tase_results if r['financial'])
    successful_pricing = sum(1 for r in us_results + tase_results if r['pricing'])

    console.print(f"[bold]תוצאות:[/bold]")
    console.print(f"  נבדקו: {total_tests} מניות")
    console.print(f"  EODHD הצליח: {successful_financial}/{total_tests}")
    console.print(f"  yfinance הצליח: {successful_pricing}/{total_tests}")
    console.print()

    if successful_financial >= len(TEST_STOCKS_US) and successful_pricing >= len(TEST_STOCKS_US):
        console.print("[green]✓ בדיקת QA עברה בהצלחה![/green]")
        console.print("[green]  האינטגרציה בין EODHD ל-yfinance עובדת כראוי[/green]")
        return True
    else:
        console.print("[yellow]⚠ בדיקת QA הושלמה עם אזהרות[/yellow]")
        console.print("[yellow]  ייתכן ויש בעיות עם חלק מהמניות[/yellow]")
        return all_tests_passed


if __name__ == "__main__":
    try:
        success = run_qa_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]הבדיקה בוטלה על ידי המשתמש[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]שגיאה:[/red] {e}")
        if settings.DEBUG_MODE:
            console.print_exception()
        sys.exit(1)
