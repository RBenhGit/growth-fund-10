#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
סקריפט בדיקה ל-EOD Historical Data API
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


def test_eodhd_connection():
    """בדיקת חיבור ל-EODHD API"""
    console.print(Panel.fit("[bold cyan]בדיקת EOD Historical Data API[/bold cyan]"))
    console.print()

    # בדיקת API key
    if not settings.EODHD_API_KEY:
        console.print("[red]שגיאה:[/red] חסר EODHD_API_KEY ב-.env")
        return False

    console.print(f"[yellow]API Key:[/yellow] {settings.EODHD_API_KEY[:10]}...")
    console.print()

    base_url = "https://eodhd.com/api"

    try:
        # 1. בדיקת fundamentals - Apple (US)
        console.print("[cyan]1. בודק נתונים פונדמנטליים (AAPL.US)...[/cyan]")
        url = f"{base_url}/fundamentals/AAPL.US"
        params = {
            "api_token": settings.EODHD_API_KEY,
            "fmt": "json"
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] שגיאה: {response.status_code}")
            console.print(f"Response: {response.text[:500]}")
            return False

        data = response.json()
        if not data:
            console.print("[red]✗[/red] לא התקבל מידע")
            return False

        general = data.get("General", {})
        highlights = data.get("Highlights", {})
        console.print(f"[green]✓[/green] {general.get('Name', 'N/A')}")
        console.print(f"  סימול: {general.get('Code', 'N/A')}")
        console.print(f"  סקטור: {general.get('Sector', 'N/A')}")
        console.print(f"  מחיר: ${highlights.get('MarketCapitalization', 0) / 1e9:.2f}B שווי שוק")
        console.print()

        # 2. בדיקת income statement
        console.print("[cyan]2. בודק דוחות רווח והפסד (AAPL.US)...[/cyan]")
        financials = data.get("Financials", {})
        income_statements = financials.get("Income_Statement", {}).get("yearly", {})

        if not income_statements:
            console.print("[red]✗[/red] לא התקבלו דוחות")
            return False

        console.print(f"[green]✓[/green] התקבלו {len(income_statements)} דוחות שנתיים")

        # הצגת טבלה
        table = Table(title="דוחות רווח והפסד - Apple")
        table.add_column("שנה", style="cyan")
        table.add_column("הכנסות", style="green", justify="right")
        table.add_column("רווח נקי", style="yellow", justify="right")
        table.add_column("EBITDA", style="magenta", justify="right")

        sorted_years = sorted(income_statements.keys(), reverse=True)[:5]
        for year in sorted_years:
            stmt = income_statements[year]
            table.add_row(
                year,
                f"${float(stmt.get('totalRevenue', 0)):,.0f}",
                f"${float(stmt.get('netIncome', 0)):,.0f}",
                f"${float(stmt.get('ebitda', 0)):,.0f}"
            )

        console.print(table)
        console.print()

        # 3. בדיקת מניה ישראלית (TASE)
        console.print("[cyan]3. בודק מניה ישראלית (TEVA.TA)...[/cyan]")
        url = f"{base_url}/fundamentals/TEVA.TA"
        params = {
            "api_token": settings.EODHD_API_KEY,
            "fmt": "json"
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            console.print(f"[yellow]⚠[/yellow] לא ניתן לגשת ל-TASE (אולי דורש מנוי מתקדם)")
            console.print(f"  Status: {response.status_code}")
        else:
            teva_data = response.json()
            teva_general = teva_data.get("General", {})
            console.print(f"[green]✓[/green] {teva_general.get('Name', 'TEVA')}")
            console.print(f"  סימול: {teva_general.get('Code', 'TEVA')}")
        console.print()

        # 4. בדיקת S&P 500 constituents
        console.print("[cyan]4. בודק רשימת S&P 500...[/cyan]")
        url = f"{base_url}/exchange-symbol-list/US"
        params = {
            "api_token": settings.EODHD_API_KEY,
            "fmt": "json",
            "type": "common_stock"
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] שגיאה: {response.status_code}")
            return False

        us_stocks = response.json()
        console.print(f"[green]✓[/green] נמצאו {len(us_stocks)} מניות בבורסה האמריקאית")

        # הצגת 10 הראשונות
        console.print("\n[bold]10 מניות ראשונות:[/bold]")
        for stock in us_stocks[:10]:
            console.print(f"  • {stock['Code']:6} - {stock['Name'][:50]}")

        console.print()
        console.print("[green]✓[/green] כל הבדיקות עברו בהצלחה!")
        console.print()
        console.print("[yellow]הערה:[/yellow] EODHD מספק גישה למידע רב עבור מניות אמריקאיות וישראליות")
        console.print("[yellow]       [/yellow] נתוני TASE עשויים לדרוש מנוי מתקדם")

        return True

    except requests.exceptions.RequestException as e:
        console.print(f"[red]שגיאת רשת:[/red] {e}")
        return False
    except Exception as e:
        console.print(f"[red]שגיאה:[/red] {e}")
        if settings.DEBUG_MODE:
            console.print_exception()
        return False


if __name__ == "__main__":
    success = test_eodhd_connection()
    sys.exit(0 if success else 1)
