# תכנית פיתוח מערכת בניית קרן צמיחה 8

## 1. סקירה כללית

### מטרת המערכת
מערכת אוטומטית לבניית קרן השקעות בת 8 מניות (6 בסיס + 2 פוטנציאל) על בסיס שני מדדים:
- **מדד ת"א 125** - 125 המניות הגדולות בבורסה הישראלית
- **מדד S&P500** - 500 המניות הגדולות בבורסה האמריקאית

**מקור נתונים יחיד:** Investing.com Pro (עם פרטי התחברות מ-[.env](.env))

### תהליך בניית הקרן (14 שלבים)
לפי [Fund_Update_Instructions.md](Fund_Update_Instructions.md)

---

## 2. ניתוח דרישות נתונים

### נתונים פיננסיים נדרשים מ-Investing.com

#### עבור מניות בסיס (5 שנים אחורה):
- ✓ **רווח נקי** (Net Income) - חיובי ברצף 5 שנים
- ✓ **הכנסות** (Revenue) - לחישוב צמיחה
- ✓ **רווח תפעולי** (Operating Income) - חיובי ב-4/5 שנים
- ✓ **תזרים מזומנים מפעילות שוטפת** (Operating Cash Flow) - חיובי במרבית השנים
- ✓ **חוב/הון עצמי** (Total Debt / Total Equity) - מתחת ל-60%
- ✓ **שווי שוק** (Market Cap) - לציון גודל

#### עבור מניות פוטנציאל (2-3 שנים):
- ✓ רווח נקי - חיובי 2 שנים
- ✓ הכנסות - לחישוב צמיחה
- ✓ מחיר נוכחי
- ✓ מחיר לפני 12 חודשים - למומנטום
- ✓ P/E Ratio - לציון שווי

#### נתוני מדדים:
- ✓ רשימת רכיבי המדד (ת"א 125 / S&P500)
- ✓ סימולים (tickers)
- ✓ P/E ממוצע של המדד

---

## 3. ארכיטקטורה מוצעת

### מבנה תיקיות

```
קרן_צמיחה_8/
├── .env                              # ✅ קיים - הגדרות
├── requirements.txt                  # תלויות Python
├── build_fund.py                     # ⭐ סקריפט ראשי
├── README.md                         # תיעוד השימוש
│
├── config/
│   └── settings.py                   # קריאת .env וניהול הגדרות
│
├── data_sources/
│   ├── __init__.py
│   ├── base_data_source.py          # Abstract base class
│   └── investing_scraper.py         # ⭐ Investing.com Selenium
│
├── fund_builder/
│   ├── __init__.py
│   ├── data_collector.py            # ⭐ איסוף נתונים (orchestrator)
│   ├── stock_screener.py            # ⭐ סינון מניות (שלבים 2,6)
│   ├── scorer.py                    # ⭐ חישוב ציונים (שלבים 3,7)
│   ├── fund_composer.py             # ⭐ הרכבת קרן (שלבים 9-11)
│   └── validators.py                # ⭐ ולידציה (שלב 14)
│
├── models/
│   ├── __init__.py
│   ├── stock.py                     # מחלקת Stock
│   ├── fund.py                      # מחלקת Fund
│   └── financial_data.py            # נתונים פיננסיים
│
├── utils/
│   ├── __init__.py
│   ├── calculations.py              # חישובים מתמטיים
│   ├── date_utils.py                # ניהול תאריכים ורבעונים
│   ├── cache_manager.py             # ניהול cache
│   └── report_generator.py          # ⭐ יצירת מסמכי MD (שלבים 12-13)
│
├── tests/
│   ├── test_investing_scraper.py
│   ├── test_scorer.py
│   └── test_validators.py
│
├── cache/                            # נתונים שמורים
│   ├── stocks_data/
│   └── index_constituents/
│
└── Fund_Docs/                        # ⭐ פלט - מסמכי קרן
    ├── Fund_8_TASE_Q4_2025.md
    ├── Fund_8_SP500_Q4_2025.md
    └── Fund_8_Q4_2025_Update.md
```

### תרשים זרימה

```
build_fund.py
    ↓
config.settings (קריאת .env)
    ↓
data_collector.py
    ↓
investing_scraper.py (איסוף נתונים)
    ↓ (נתונים גולמיים)
    ↓
stock_screener.py (סינון - שלבים 2,6)
    ↓ (מניות כשרות)
    ↓
scorer.py (חישוב ציונים - שלבים 3,7)
    ↓ (מניות מדורגות)
    ↓
fund_composer.py (בחירת מניות ומשקלים - שלבים 4,8,9)
    ↓ (הרכב קרן)
    ↓
validators.py (בדיקות שלב 14)
    ↓ (✓ אימות עבר)
    ↓
report_generator.py (יצירת MD - שלבים 12-13)
    ↓
Fund_Docs/*.md
```

---

## 4. תכנון Investing.com Scraper

### תהליך שליפת נתונים

#### שלב א': התחברות
```python
1. פתיחת Chrome עם Selenium
2. ניווט ל-https://www.investing.com/
3. לחיצה על כפתור Sign In
4. מילוי email + password מ-.env
5. המתנה לטעינת דף הבית
6. שמירת session
```

#### שלב ב': שליפת רשימת מניות במדד

**עבור ת"א 125:**
```python
URL: https://www.investing.com/indices/ta-125-components
1. ניווט לעמוד רכיבי המדד
2. שליפת טבלת המניות
3. חילוץ: שם חברה, סימול, שווי שוק
```

**עבור S&P500:**
```python
URL: https://www.investing.com/indices/us-spx-500-components
1. ניווט לעמוד רכיבי המדד
2. שליפת טבלת המניות
3. חילוץ: שם חברה, סימול, שווי שוק
```

#### שלב ג': שליפת נתונים פיננסיים למניה

**עבור כל מניה:**
```python
1. ניווט לעמוד המניה (לפי URL)
2. לחיצה על טאב "Financials"

3. Income Statement:
   - Revenue (5 שנים)
   - Net Income (5 שנים)
   - Operating Income (5 שנים)

4. Balance Sheet:
   - Total Debt
   - Total Equity

5. Cash Flow Statement:
   - Operating Cash Flow (5 שנים)

6. דף ראשי:
   - Market Cap
   - Current Price
   - P/E Ratio
   - היסטוריית מחירים (12 חודשים)
```

### טיפול ב-Cache

**מבנה Cache:**
```
cache/
├── index_constituents/
│   ├── TASE125_2025-11-27.json
│   └── SP500_2025-11-27.json
└── stocks_data/
    ├── AAPL_2025-11-27.json
    ├── MSFT_2025-11-27.json
    └── ...
```

**לוגיקת Cache:**
```python
1. בדוק אם יש נתונים ב-cache (מאותו יום)
2. אם כן - השתמש ב-cache
3. אם לא - שלוף מ-Investing.com ושמור ב-cache
4. אפשרות לכפות refresh עם --no-cache
```

**מדוע חשוב:**
- Selenium איטי - חסכון בזמן
- הימנעות מחסימות (rate limiting)
- אפשרות לעבודה offline לאחר שליפה ראשונה

---

## 5. תכנון החישובים המתמטיים

### 5.1 חישוב צמיחה שנתית (מניות בסיס)

```python
def calculate_partial_year_growth(current_value, prev_year_value, quarters_elapsed):
    """
    צמיחה_שנתית_חלקית = ((ערך_נוכחי - ערך_שנה_קודמת) / ערך_שנה_קודמת) × (1 + quarters/4) × 100
    """
    growth = ((current_value - prev_year_value) / prev_year_value) * (1 + quarters_elapsed/4) * 100
    return growth

def calculate_annual_growth(current_value, prev_value):
    """
    צמיחה_שנתית = ((ערך_נוכחי - ערך_קודם) / ערך_קודם) × 100
    """
    return ((current_value - prev_value) / prev_value) * 100

def calculate_weighted_average_growth(partial_2025, growth_2024, growth_2023):
    """
    צמיחה_ממוצעת = (צמיחה_חלקית_2025 × 0.4) + (צמיחה_2024 × 0.35) + (צמיחה_2023 × 0.25)
    """
    return (partial_2025 * 0.4) + (growth_2024 * 0.35) + (growth_2023 * 0.25)
```

### 5.2 נורמליזציה לציון 0-100

```python
def normalize_to_score(value, min_value, max_value):
    """
    ציון_נורמלי = ((ערך_חברה - ערך_מינימלי) / (ערך_מקסימלי - ערך_מינימלי)) × 100
    """
    if max_value == min_value:
        return 50  # ברירת מחדל אם אין שונות
    return ((value - min_value) / (max_value - min_value)) * 100
```

### 5.3 חישוב ציון בסיס

```python
def calculate_base_score(stock, all_stocks):
    """
    ציון_סופי = (ציון_צמיחת_רווח × 0.40) + (ציון_צמיחת_הכנסות × 0.35) + (ציון_גודל × 0.25)
    """
    # 1. חישוב צמיחות
    net_income_growth = calculate_weighted_average_growth(...)
    revenue_growth = calculate_weighted_average_growth(...)
    market_cap = stock.market_cap

    # 2. מציאת min/max ביחס לכל המניות
    min_income, max_income = get_min_max([s.net_income_growth for s in all_stocks])
    min_revenue, max_revenue = get_min_max([s.revenue_growth for s in all_stocks])
    min_cap, max_cap = get_min_max([s.market_cap for s in all_stocks])

    # 3. נורמליזציה
    income_score = normalize_to_score(net_income_growth, min_income, max_income)
    revenue_score = normalize_to_score(revenue_growth, min_revenue, max_revenue)
    size_score = normalize_to_score(market_cap, min_cap, max_cap)

    # 4. ציון משוקלל
    final_score = (income_score * 0.40) + (revenue_score * 0.35) + (size_score * 0.25)

    return final_score
```

### 5.4 חישוב ציון פוטנציאל

```python
def calculate_potential_score(stock, all_stocks, index_avg_pe):
    """
    ציון_פוטנציאל = (ציון_צמיחה_עתידית × 0.5) + (ציון_מומנטום × 0.3) + (ציון_שווי × 0.2)
    """
    # 1. צמיחה עתידית
    growth_23_24 = calculate_annual_growth(...)
    growth_24_25 = calculate_annual_growth(...)
    estimated_25_26 = (growth_23_24 + growth_24_25) / 2 * 0.8
    future_growth = (growth_23_24 * 0.2) + (growth_24_25 * 0.4) + (estimated_25_26 * 0.4)

    # 2. מומנטום (12 חודשים)
    momentum = ((current_price - price_12m_ago) / price_12m_ago) * 100

    # 3. שווי (P/E יחסי)
    relative_pe = stock.pe_ratio / index_avg_pe
    valuation_score = 100 - ((relative_pe - 0.5) / (2.5 - 0.5)) * 100

    # 4. נורמליזציה
    future_growth_score = normalize_to_score(future_growth, ...)
    momentum_score = normalize_to_score(momentum, ...)

    # 5. ציון משוקלל
    final_score = (future_growth_score * 0.5) + (momentum_score * 0.3) + (valuation_score * 0.2)

    return final_score
```

### 5.5 חישוב עלות מינימלית (LCM)

```python
from math import gcd
from functools import reduce

def lcm(a, b):
    return abs(a * b) // gcd(a, b)

def calculate_minimum_fund_cost(stocks, weights):
    """
    מוצא LCM של כל המחירים המשוקללים
    כך שכל מניה תתקבל במספר שלם
    """
    # 1. חישוב עלות חלקית לכל מניה
    partial_costs = [stock.price * weight for stock, weight in zip(stocks, weights)]

    # 2. המרה למכפילים (עיגול ל-2 ספרות)
    multipliers = [int(cost * 100) for cost in partial_costs]

    # 3. מציאת LCM של כל המכפילים
    lcm_value = reduce(lcm, multipliers)

    # 4. חישוב עלות מינימלית
    min_cost = lcm_value / 100

    return min_cost
```

---

## 6. קומפוננטות עיקריות

### 6.1 InvestingScraper
```python
class InvestingScraper:
    def __init__(self, email: str, password: str)
    def login() -> bool
    def get_index_constituents(index_name: str) -> List[Dict]
    def get_stock_financials(symbol: str, years: int = 5) -> FinancialData
    def get_stock_market_data(symbol: str) -> MarketData
    def get_stock_price_history(symbol: str, days: int = 365) -> List[PricePoint]
    def logout()
```

### 6.2 StockScreener
```python
class StockScreener:
    def filter_base_stocks(stocks: List[Stock]) -> List[Stock]:
        """שלב 2: סינון לפי 5 קריטריונים"""

    def filter_potential_stocks(stocks: List[Stock], base_stocks: List[Stock]) -> List[Stock]:
        """שלב 6: סינון לפי 4 קריטריונים"""
```

### 6.3 Scorer
```python
class Scorer:
    def calculate_base_score(stock: Stock, all_stocks: List[Stock]) -> float:
        """שלב 3: חישוב ציון מניות בסיס"""

    def calculate_potential_score(stock: Stock, all_stocks: List[Stock], index_pe: float) -> float:
        """שלב 7: חישוב ציון מניות פוטנציאל"""
```

### 6.4 FundComposer
```python
class FundComposer:
    WEIGHTS = [0.25, 0.20, 0.15, 0.12, 0.10, 0.06, 0.06, 0.06]

    def select_top_stocks(scored_stocks: List[Stock], count: int) -> List[Stock]:
        """שלבים 4,8: בחירת מניות"""

    def assign_weights(stocks: List[Stock]) -> Dict[str, float]:
        """שלב 9: הקצאת משקלים"""

    def calculate_minimum_fund_cost(stocks: List[Stock], weights: Dict) -> float:
        """שלב 10: חישוב עלות מינימלית"""
```

### 6.5 FundValidator
```python
class FundValidator:
    def validate_weights_sum_100(fund: Fund) -> bool
    def validate_base_stocks_eligibility(stocks: List[Stock]) -> bool
    def validate_potential_stocks_eligibility(stocks: List[Stock]) -> bool
    def validate_no_overlap(base: List[Stock], potential: List[Stock]) -> bool
    def validate_index_membership(stocks: List[Stock], index: str) -> bool
    def validate_whole_shares(fund: Fund) -> bool
    def validate_cost_calculation(fund: Fund) -> bool
```

### 6.6 ReportGenerator
```python
class ReportGenerator:
    def generate_ranking_table(stocks: List[Stock], scores: Dict) -> str
    def generate_fund_composition_table(fund: Fund) -> str
    def generate_update_report(...) -> str  # שלב 12
    def generate_fund_report(fund: Fund, index_name: str) -> str  # שלב 13
```

---

## 7. תכנית יישום (Implementation Phases)

### Phase 1: תשתית בסיסית ⭐
**זמן משוער: 2-3 שעות**

**משימות:**
1. יצירת `requirements.txt`
2. יצירת `config/settings.py`
3. יצירת `utils/date_utils.py`
4. יצירת models: `Stock`, `Fund`, `FinancialData`, `MarketData`
5. יצירת `build_fund.py` - CLI בסיסי

**פלט:**
```bash
python build_fund.py --index TASE125
python build_fund.py --index SP500
```

### Phase 2: Investing.com Scraper ⭐⭐⭐
**זמן משוער: 8-12 שעות**

**משימות:**
1. התקנת Selenium + WebDriver Manager
2. יצירת `data_sources/investing_scraper.py`
3. מימוש `login()` עם פרטים מ-.env
4. מימוש `get_index_constituents()`
5. מימוש `get_stock_financials()`
6. מימוש `get_stock_market_data()`
7. הוספת retry logic וטיפול בשגיאות
8. **בדיקה ידנית עם 3-5 מניות**

**אתגרים:**
- זיהוי HTML selectors נכונים
- טיפול ב-loading states
- יציבות (timeouts, network errors)

### Phase 3: Cache Manager ⭐
**זמן משוער: 2-3 שעות**

**משימות:**
1. יצירת `utils/cache_manager.py`
2. שמירת/קריאת JSON מ-`cache/`
3. בדיקת תקפות cache (תאריך)
4. אפשרות `--no-cache`

### Phase 4: Stock Screener ⭐
**זמן משוער: 3-4 שעות**

**משימות:**
1. יצירת `fund_builder/stock_screener.py`
2. מימוש `filter_base_stocks()` - 5 קריטריונים
3. מימוש `filter_potential_stocks()` - 4 קריטריונים
4. בדיקה עם נתוני דמה

### Phase 5: Scorer ⭐⭐
**זמן משוער: 4-6 שעות**

**משימות:**
1. יצירת `utils/calculations.py`
2. יצירת `fund_builder/scorer.py`
3. מימוש `calculate_base_score()`
4. מימוש `calculate_potential_score()`
5. בדיקה עם נתוני דמה

### Phase 6: Fund Composer ⭐
**זמן משוער: 3-4 שעות**

**משימות:**
1. יצירת `fund_builder/fund_composer.py`
2. מימוש `select_top_stocks()`
3. מימוש `assign_weights()`
4. מימוש `calculate_minimum_fund_cost()`

### Phase 7: Validators ⭐
**זמן משוער: 2-3 שעות**

**משימות:**
1. יצירת `fund_builder/validators.py`
2. מימוש 7 בדיקות שלב 14
3. דיווח על כשלים

### Phase 8: Report Generator ⭐
**זמן משוער: 2-3 שעות**

**משימות:**
1. יצירת `utils/report_generator.py`
2. מימוש טבלאות Markdown
3. יצירת 3 מסמכים (שלבים 12-13)

### Phase 9: Integration & Testing ⭐⭐
**זמן משוער: 4-6 שעות**

**משימות:**
1. בניית קרן מלאה מקצה לקצה
2. בדיקה עם ת"א 125
3. בדיקה עם S&P500
4. תיקון באגים

### Phase 10: Documentation & Polish ⭐
**זמן משוער: 2-3 שעות**

**משימות:**
1. כתיבת `README.md`
2. דוגמאות שימוש
3. הוספת progress bars (rich library)
4. שיפור הודעות שגיאה

---

## 8. טכנולוגיות

### תלויות Python

```txt
# requirements.txt

# Core
selenium==4.15.2
webdriver-manager==4.0.1

# Data
pandas==2.1.4
python-dotenv==1.0.0
pydantic==2.5.3

# Utils
rich==13.7.0          # progress bars + pretty CLI
loguru==0.7.2         # logging

# Testing (optional)
pytest==7.4.3
```

---

## 9. סיכונים ואתגרים

### סיכונים טכניים

1. **Investing.com scraper לא יציב**
   - שינויי UI עלולים לשבור את הקוד
   - **פתרון:** בניית selectors גמישים, logging מפורט

2. **נתונים חסרים**
   - לא כל המניות יכולות להיות בעלות 5 שנות נתונים
   - **פתרון:** דיווח ברור + skip

3. **Rate Limiting / Captcha**
   - Investing.com עשוי לחסום
   - **פתרון:** cache, delays, manual intervention

4. **זמן ריצה ארוך**
   - Selenium איטי (125 מניות × 5 שנים = המון דפים)
   - **פתרון:** cache + progress bars

---

## 10. סיכום

### גישה מומלצת: PoC → הרחבה

**שלב 1: Proof of Concept**
- בניית scraper ל-**5 מניות בודדות** מ-S&P500
- הרצת pipeline מלא (data → filter → score → fund → report)
- בדיקה ידנית מול נתונים אמיתיים

**שלב 2: הרחבה**
- תמיכה במדד מלא (125/500 מניות)
- תמיכה בשני המדדים
- cache מלא

**שלב 3: ייצור**
- בדיקות אוטומטיות
- תיעוד מלא
- CLI מלא עם progress bars

---

**הערכת זמן כוללת: 32-47 שעות פיתוח**

**קובץ ראשון להתחיל בו:** `requirements.txt`

---

**סיום תכנית** 🎯
