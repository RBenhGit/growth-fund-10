"""
Verify S&P 500 Index Constituents
בדיקת עדכניות רכיבי מדד S&P 500
"""

import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from data_sources.twelvedata_api import TwelveDataSource
from config import settings
import json

def main():
    print("🔍 בודק רכיבי מדד S&P 500...")
    print(f"📡 מקור נתונים: TwelveData API")
    print()

    # יצירת מקור נתונים
    data_source = TwelveDataSource()

    # בדיקת חיבור
    if not data_source.login():
        print("❌ שגיאה בחיבור ל-TwelveData API")
        return

    print("✅ חיבור תקין ל-TwelveData API")
    print()

    # שליפת רכיבי המדד
    print("📥 שולף רכיבי מדד S&P 500...")
    try:
        constituents = data_source.get_index_constituents("SP500")
        print(f"✅ נמצאו {len(constituents)} מניות במדד")
        print()

        # חיפוש PARA/PSKY
        para_stocks = [s for s in constituents if s['symbol'] in ['PARA', 'PSKY', 'PARAA']]

        if para_stocks:
            print("🎯 מניות Paramount שנמצאו:")
            for stock in para_stocks:
                print(f"  - {stock['symbol']}: {stock['name']}")
        else:
            print("⚠️  לא נמצאו מניות PARA או PSKY במדד")

        print()
        print("📊 דוגמאות ממניות במדד (10 ראשונות):")
        for i, stock in enumerate(constituents[:10]):
            print(f"  {i+1}. {stock['symbol']:6} - {stock['name']}")

        # שמירת התוצאות
        output_file = "fresh_sp500_constituents.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(constituents, f, indent=2, ensure_ascii=False)
        print()
        print(f"💾 התוצאות נשמרו ב: {output_file}")

    except Exception as e:
        print(f"❌ שגיאה בשליפת נתונים: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
