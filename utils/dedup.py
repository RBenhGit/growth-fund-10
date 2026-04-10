"""
כלי deduplication לחברות עם מספר סוגי מניות

פונקציות עזר לזיהוי ופילטור כפילויות של חברות ברשימות מניות.
"""

import re


def get_base_company_name(stock) -> str:
    """
    חילוץ שם החברה הבסיסי מתוך שם החברה או סימול

    מסיר סיומות כגון: Class A, Class B, Class C, Inc, Ltd, Corp, וכו'
    כדי לזהות חברות עם מספר סוגי מניות.

    Args:
        stock: מניה

    Returns:
        str: שם בסיסי של החברה
    """
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
        r'\s+[A-C]$',  # סיומת בודדת אחרי הסרת סיומות חברה: "News Corp A" → "News Corp" → "News"
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
    - News Corp: NWS (Class B), NWSA (Class A)

    Args:
        ranked_stocks: רשימת מניות ממוינות לפי דירוג (גבוה לנמוך)
        count: מספר מניות לבחור

    Returns:
        List[Stock]: רשימת מניות נבחרות (ללא כפילויות)
    """
    selected = []
    seen_companies = set()

    for stock in ranked_stocks:
        base_name = get_base_company_name(stock)

        if base_name in seen_companies:
            continue

        selected.append(stock)
        seen_companies.add(base_name)

        if len(selected) >= count:
            break

    return selected
