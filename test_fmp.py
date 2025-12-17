#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
סקריפט בדיקה ל-Financial Modeling Prep API
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


def test_fmp_connection():
    """בדיקת חיבור ל-FMP API"""
    console.print(Panel.fit("[bold cyan]בדיקת Financial Modeling Prep API[/bold cyan]"))
    console.print()

    # בדיקת API key
    if not settings.FMP_API_KEY:
        console.print("[red]שגיאה:[/red] חסר FMP_API_KEY ב-.env")
        return False

    console.print(f"[yellow]API Key:[/yellow] {settings.FMP_API_KEY[:8]}...")
    console.print()

    base_url = "https://financialmodelingprep.com/api/v3"

    try:
        # 1. בדיקת profile חברה - Apple
        console.print("[cyan]1. בודק פרופיל חברה (AAPL)...[/cyan]")
        url = f"{base_url}/profile/AAPL?apikey={settings.FMP_API_KEY}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] שגיאה: {response.status_code}")
            console.print(f"Response: {response.text[:500]}")
            return False

        data = response.json()
        if not data:
            console.print("[red]✗[/red] לא התקבל מידע")
            return False

        company = data[0]
        console.print(f"[green]✓[/green] {company['companyName']}")
        console.print(f"  סימול: {company['symbol']}")
        console.print(f"  מחיר: ${company['price']:.2f}")
        console.print(f"  שווי שוק: ${company['mktCap']:,}")
        console.print()

        # 2. בדיקת income statement
        console.print("[cyan]2. בודק דוחות רווח והפסד (AAPL)...[/cyan]")
        url = f"{base_url}/income-statement/AAPL?limit=5&apikey={settings.FMP_API_KEY}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] שגיאה: {response.status_code}")
            return False

        statements = response.json()
        if not statements:
            console.print("[red]✗[/red] לא התקבלו דוחות")
            return False

        console.print(f"[green]✓[/green] התקבלו {len(statements)} דוחות")

        # הצגת טבלה
        table = Table(title="דוחות רווח והפסד - Apple")
        table.add_column("שנה", style="cyan")
        table.add_column("הכנסות", style="green", justify="right")
        table.add_column("רווח נקי", style="yellow", justify="right")
        table.add_column("רווח תפעולי", style="magenta", justify="right")

        for stmt in statements[:5]:
            table.add_row(
                stmt['date'][:4],
                f"${stmt['revenue']:,.0f}",
                f"${stmt['netIncome']:,.0f}",
                f"${stmt['operatingIncome']:,.0f}"
            )

        console.print(table)
        console.print()

        # 3. בדיקת S&P 500 constituents
        console.print("[cyan]3. בודק רשימת S&P 500...[/cyan]")
        url = f"{base_url}/sp500_constituent?apikey={settings.FMP_API_KEY}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            console.print(f"[red]✗[/red] שגיאה: {response.status_code}")
            return False

        constituents = response.json()
        console.print(f"[green]✓[/green] נמצאו {len(constituents)} מניות ב-S&P 500")

        # הצגת 10 הראשונות
        console.print("\n[bold]10 מניות ראשונות:[/bold]")
        for stock in constituents[:10]:
            console.print(f"  • {stock['symbol']:6} - {stock['name'][:50]}")

        console.print()
        console.print("[green]✓[/green] כל הבדיקות עברו בהצלחה!")
        console.print()
        console.print("[yellow]הערה:[/yellow] FMP API מאפשר גישה למידע רב, אך חלק מה-endpoints דורשים מנוי בתשלום")

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
    success = test_fmp_connection()
    sys.exit(0 if success else 1)
