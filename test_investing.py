#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
סקריפט בדיקה ל-Investing.com Scraper
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from config import settings
from data_sources import InvestingScraper

console = Console()


def test_login():
    """בדיקת התחברות"""
    console.print(Panel.fit("[bold cyan]בדיקת Investing.com Scraper[/bold cyan]"))
    console.print()

    # בדיקת הגדרות
    if not settings.INVESTING_EMAIL or not settings.INVESTING_PASSWORD:
        console.print("[red]שגיאה:[/red] חסרים פרטי התחברות ב-.env")
        console.print("אנא הוסף INVESTING_EMAIL ו-INVESTING_PASSWORD")
        return False

    console.print(f"[yellow]אימייל:[/yellow] {settings.INVESTING_EMAIL}")
    console.print()

    # יצירת scraper
    console.print("[cyan]יוצר scraper...[/cyan]")
    scraper = InvestingScraper(
        email=settings.INVESTING_EMAIL,
        password=settings.INVESTING_PASSWORD,
        headless=False  # עם חלון כדי לראות מה קורה
    )

    try:
        # בדיקת התחברות
        console.print("[cyan]מתחבר ל-Investing.com...[/cyan]")
        if scraper.login():
            console.print("[green]✓[/green] התחברות הצליחה!")
        else:
            console.print("[red]✗[/red] התחברות נכשלה")
            return False

        # בדיקת שליפת רשימת מניות
        console.print()
        console.print("[cyan]שולף רשימת מניות מ-S&P500...[/cyan]")
        constituents = scraper.get_index_constituents("SP500")

        console.print(f"[green]✓[/green] נמצאו {len(constituents)} מניות")

        # הצגת 5 הראשונות
        console.print()
        console.print("[bold]5 מניות ראשונות:[/bold]")
        for stock in constituents[:5]:
            console.print(f"  • {stock['name']} ({stock['symbol']})")

        console.print()
        console.print("[green]✓[/green] כל הבדיקות עברו בהצלחה!")
        return True

    except Exception as e:
        console.print(f"[red]שגיאה:[/red] {e}")
        if settings.DEBUG_MODE:
            console.print_exception()
        return False

    finally:
        console.print()
        console.print("[cyan]מנתק...[/cyan]")
        scraper.logout()


if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)
