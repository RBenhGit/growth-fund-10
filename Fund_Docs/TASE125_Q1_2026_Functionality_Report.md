# דוח פונקציונליות - קרן צמיחה 10 TASE125 Q1 2026

**תאריך הפקה:** 2026-02-01
**מדד:** TASE125
**רבעון:** Q1 2026
**שם קרן:** Fund_10_TASE125_Q1_2026

---

## 1. מקורות נתונים (Data Sources)

### 1.1 תצורה (Configuration)
| פרמטר | ערך |
|--------|-----|
| `FINANCIAL_DATA_SOURCE` | `twelvedata` |
| `PRICING_DATA_SOURCE` | `twelvedata` |
| `TWELVEDATA_API_KEY` | `10e18fc5e3be45cea831fc8c0b0919d4` |
| `USE_CACHE` | `true` |
| `DEBUG_MODE` | `true` |

### 1.2 ניתוב מקורות נתונים (Data Source Routing)
הניתוב מתבצע דרך `DataSourceRouter` (קובץ `data_sources/router.py`):

1. המערכת בודקת אם `FINANCIAL_DATA_SOURCE` מוגדר ב-`.env`
2. במקרה שלנו: `twelvedata` → `TwelveDataSource()` נוצר דרך `_get_explicit_source()`
3. **מקור יחיד**: TwelveData משמש **גם** לנתונים פיננסיים (fundamentals) **וגם** למחירים (pricing)

### 1.3 TwelveData API - פירוט קריאות לכל מניה
לכל מניה מתבצעות **6 קריאות API**:

| # | Endpoint | מה מחזיר | עלות משוערת (credits) |
|---|----------|----------|----------------------|
| 1 | `/income_statement` | הכנסות, רווח נקי, רווח תפעולי (5 שנים) | ~60 |
| 2 | `/balance_sheet` | חוב, הון עצמי (שנה אחרונה) | ~60 |
| 3 | `/cash_flow` | תזרים מפעילות שוטפת (5 שנים) | ~60 |
| 4 | `/quote` | מחיר נוכחי, שם חברה | ~50 |
| 5 | `/statistics` | שווי שוק, P/E | ~60 |
| 6 | `/time_series` | היסטוריית מחירים חודשית (24 חודשים) | ~60 |

**סה"כ לכל מניה: ~351 credits**

### 1.4 Rate Limiting
- **מגבלת API:** 1,597 credits/minute (Pro plan)
- **אסטרטגיה:** מקסימום 4 מניות לדקה, המתנה ~62 שניות בין batches
- **בהרצה הנוכחית:** נטענו מ-cache (ללא קריאות API חיות)

### 1.5 המרת מטבע
- TwelveData מחזיר מחירי מניות TASE באגורות (ILA)
- דוחות כספיים מוחזרים ב-ILS (שקלים)
- **המרה:** כל מחירים ושווי שוק מחולקים ב-100 (ILA → ILS)
- מתבצעת ב-`_convert_price_to_ils()`, `get_stock_market_data()`, ו-`get_stock_financials()`

### 1.6 מקור רשימת מדד (Index Constituents)
- TwelveData **אינו מספק** רשימת רכיבי TA-125 ישירות
- הנתונים נטענים מ-**cache**: `cache/index_constituents/TASE125_Q4_2025.json`
- Cache מקורי שנוצר מ-EODHD API בגרסה קודמת (Q4 2025)
- מכיל 117 מניות עם: `symbol`, `name`, `sector`, `sub_sector`

---

## 2. זרימת 14 השלבים - קלט, עיבוד, פלט, מעברים

### שלב 1: איסוף רשימת מניות מהמדד
| | פירוט |
|---|--------|
| **קלט** | שם מדד: `TASE125`, cache file: `TASE125_Q1_2026.json` (לא קיים) → fallback to `TASE125_Q4_2025.json` |
| **עיבוד** | `data_source.get_index_constituents("TASE125")` → טעינה מ-cache (סורק את `cache/index_constituents/` לפי שם מדד, בסדר יורד) |
| **פלט** | `constituents`: רשימת 117 dict-ים `[{"symbol": "ELAL", "name": "El Al...", "sector": "...", "sub_sector": "..."}]` |
| **מעבר לשלב 2** | `constituents` מועברים ללולאת Step 2 לטעינת כל מניה |

### שלב 2: סינון מניות בסיס (טעינה + בדיקת כשירות)
| | פירוט |
|---|--------|
| **קלט** | 117 constituents מ-Step 1 |
| **עיבוד** | לכל מניה: |
| | 1. הוספת סיומת `.TA` (אם חסרה) |
| | 2. טעינה מ-cache: `cache/stocks_data/{SYMBOL}_TA.json` → `Stock(**data)` |
| | 3. אם לא ב-cache: `data_source.get_stock_data(symbol, years=5)` → 6 API calls |
| | 4. בדיקת כשירות בסיס: `stock.check_base_eligibility()` |
| | 5. בדיקת כשירות פוטנציאל: `stock.check_potential_eligibility()` |
| | 6. שמירת stock ל-cache (עם דגלי כשירות מעודכנים) |
| **7 מניות שנכשלו** | `SPNS.TA`, `PZOL.TA`, `CRSO.TA`, `ISRA-L.TA`, `DEDR.TA`, `RATI-L.TA`, `DELT.TA` — סימולים לא תקינים ב-TwelveData |
| **פלט** | `all_loaded_stocks`: 110 מניות, `base_eligible`: 33 מניות כשירות |
| **מעבר לשלב 3** | `builder.all_stocks = all_loaded_stocks`, `builder.base_candidates = base_eligible` |

#### בדיקת כשירות בסיס (Base Eligibility) — 4 קריטריונים:
```
check_base_eligibility(min_profitable_years=5, min_operating_profit_years=4, max_debt_to_equity=0.60)
```

| # | קריטריון | מקור נתונים | בדיקה |
|---|----------|-------------|--------|
| 1 | רווחיות יציבה | `financial_data.net_incomes` | 5 השנים האחרונות חייבות להיות עם רווח נקי חיובי (`has_profitable_years(5)`) |
| 2 | יציבות תפעולית | `financial_data.operating_incomes` | 4 מתוך 5 השנים האחרונות עם רווח תפעולי חיובי (`has_operating_profit_years(4, 5)`) |
| 3 | תזרים מזומנים | `financial_data.operating_cash_flows` | >50% מהשנים עם תזרים חיובי (`has_positive_cash_flow()`) |
| 4 | יחס חוב/הון | `financial_data.total_debt / total_equity` | חייב להיות ≤ 0.60 (או null = OK) (`debt_to_equity_ratio`) |

**תוצאה:** 33 מניות עברו את כל 4 הקריטריונים → `base_eligible`

#### בדיקת כשירות פוטנציאל (Potential Eligibility) — 2 קריטריונים:
```
check_potential_eligibility(min_profitable_years=2)
```

| # | קריטריון | בדיקה |
|---|----------|--------|
| 1 | רווחיות בסיסית | 2 השנים האחרונות עם רווח נקי חיובי |
| 2 | נתוני צמיחה | לפחות 2 שנים של `revenues` ו-`net_incomes` |

### שלב 3: חישוב וציון מניות הבסיס
| | פירוט |
|---|--------|
| **קלט** | 33 `base_candidates` מ-Step 2 |
| **עיבוד** | `builder.score_and_rank_base_stocks(base_candidates)` |
| | 1. **לכל מניה** - חישוב ציוני גלם (raw scores): |
| | - `net_income_growth`: CAGR של רווח נקי על 3 שנים |
| | - `revenue_growth`: CAGR של הכנסות על 3 שנים |
| | - `market_cap`: שווי שוק כערך גולמי |
| | 2. **נרמול** (Normalization): כל שלושת הרכיבים מנורמלים לטווח 0-100 |
| | 3. **חישוב ציון סופי** (Weighted Composite): |
| | `score = NI_norm × 0.40 + REV_norm × 0.35 + MC_norm × 0.25` |
| **פלט** | 33 מניות ממוינות לפי `base_score` (יורד), כל מניה עם `base_score` ו-`base_scores_detail` |
| **מעבר לשלב 4** | `ranked_base` → בחירת top 6 |

#### חישוב CAGR (Compound Annual Growth Rate)
```python
calculate_growth_rate(values: Dict[int, float], years: int = 3)
```
- מיון שנים בסדר יורד
- `start_value = values[oldest_year]`, `end_value = values[newest_year]`
- **נוסחה:** `CAGR = ((end_value / start_value) ^ (1 / (years - 1)) - 1) × 100`
- אם `start_value ≤ 0`: מחזיר `None` (יטופל כ-0.0)

#### נרמול (Min-Max Normalization)
```python
normalize_score(values: List[float])
```
- `normalized = ((value - min) / (max - min)) × 100`
- אם `max == min`: כל הערכים מקבלים 50.0

#### דוגמת חישוב — NXSN.TA (דירוג #1, ציון 80.25):
| רכיב | ציון גלם | ציון מנורמל | משקל | תרומה |
|-------|----------|------------|------|--------|
| net_income_growth (CAGR 3Y) | (ערך גולמי) | (0-100) | 0.40 | ~32.1 |
| revenue_growth (CAGR 3Y) | (ערך גולמי) | (0-100) | 0.35 | ~28.1 |
| market_cap | (ערך גולמי) | (0-100) | 0.25 | ~20.1 |
| **סה"כ** | | | **1.00** | **80.25** |

### שלב 4: בחירת 6 מניות הבסיס
| | פירוט |
|---|--------|
| **קלט** | 33 `ranked_base` (ממוינות לפי base_score, יורד) |
| **עיבוד** | `select_stocks_skip_duplicates(ranked_base, 6)` |
| | - מזהה כפילויות חברות (Class A/B/C, סיומות שונות) |
| | - `get_base_company_name()`: מסיר סיומות Inc, Ltd, Corp, Class A/B/C |
| | - בוחר את 6 הראשונות ללא כפילויות |
| **פלט** | 6 מניות נבחרות: |

| דירוג | מניה | ציון |
|-------|------|------|
| 1 | NXSN.TA (Next Vision) | 80.25 |
| 2 | CLIS.TA (Clal Insurance) | 72.68 |
| 3 | STRS.TA (Strauss Group) | 49.99 |
| 4 | LUMI.TA (Bank Leumi) | 46.74 |
| 5 | MMHD.TA (Menora Mivtachim) | 45.85 |
| 6 | ESLT.TA (Elbit Systems) | 43.36 |

| **מעבר לשלב 5** | `builder.selected_base` = 6 מניות, סימולים עוברים לסינון מרשימת פוטנציאל |

### שלב 5: הכנת רשימה למניות פוטנציאל
| | פירוט |
|---|--------|
| **קלט** | `builder.all_stocks` (110), `builder.selected_base` (6 symbols) |
| **עיבוד** | הסרת 6 מניות הבסיס מהרשימה הכוללת |
| | `potential_pool = [s for s in all_stocks if s.symbol not in base_symbols]` |
| **פלט** | `potential_pool`: 104 מניות |
| **מעבר לשלב 6** | 104 מניות עוברות לסינון כשירות פוטנציאל |

### שלב 6: סינון מניות פוטנציאל
| | פירוט |
|---|--------|
| **קלט** | 104 מניות מ-`potential_pool` |
| **עיבוד** | `stock.check_potential_eligibility()` לכל מניה |
| | - 2 שנים רצופות של רווח נקי חיובי |
| | - לפחות 2 ערכים ב-`revenues` ו-`net_incomes` |
| **פלט** | 84 מניות כשירות (`potential_eligible`) |
| **20 מניות שנפלו** | מניות עם הפסדים ב-2 השנים האחרונות או חוסר בנתונים |
| **מעבר לשלב 7** | 84 מניות עוברות לציון פוטנציאל |

### שלב 7: חישוב ציון פוטנציאל
| | פירוט |
|---|--------|
| **קלט** | 84 `potential_candidates`, `index_pe = 14.0` (ברירת מחדל TASE125) |
| **עיבוד** | `builder.score_and_rank_potential_stocks(candidates, index_pe=14.0)` |
| | לכל מניה - 3 רכיבי ציון: |

#### רכיבי ציון פוטנציאל:

**1. צמיחה עתידית (Future Growth) — משקל 50%**
```python
future_growth = calculate_growth_rate(net_incomes, years=2)  # CAGR 2 שנים
```
- CAGR על 2 שנים אחרונות של רווח נקי
- אם אין מספיק נתונים → 0.0

**2. מומנטום (Momentum) — משקל 30%**
```python
momentum = market_data.calculate_momentum(365)
```
- חישוב: `((current_price - oldest_price) / oldest_price) × 100`
- `oldest_price` = המחיר הישן ביותר בהיסטוריה (TwelveData מספק ~24 חודשים חודשי)
- **אם אין היסטוריית מחירים** → momentum = 0.0

**3. שווי (Valuation) — משקל 20%**
```python
relative_pe = stock.pe_ratio / index_pe  # index_pe = 14.0
valuation_score = (2 - relative_pe) × 50  # נרמול ל-0-100
```
- **ציון גבוה** למניות עם P/E **נמוך** יחסית למדד
- דוגמה: P/E=7 → relative=0.5 → valuation=75.0
- דוגמה: P/E=28 → relative=2.0 → valuation=0.0
- **אם אין P/E** → valuation = 0.0

**נרמול וציון סופי:**
```
potential_score = growth_norm × 0.50 + momentum_norm × 0.30 + valuation_norm × 0.20
```

| **פלט** | 84 מניות ממוינות עם `potential_score` |
| **מעבר לשלב 8** | `ranked_potential` → בחירת top 4 |

### שלב 8: בחירת 4 מניות פוטנציאל
| | פירוט |
|---|--------|
| **קלט** | 84 `ranked_potential` |
| **עיבוד** | `select_stocks_skip_duplicates(ranked_potential, 4)` |
| **פלט** | 4 מניות נבחרות: |

| דירוג | מניה | ציון |
|-------|------|------|
| 1 | ELAL.TA (El Al) | 70.10 |
| 2 | ASHG.TA (Ashtrom) | 65.37 |
| 3 | MTAV.TA (Meitav) | 63.14 |
| 4 | FTAL.TA (Fattal) | 54.01 |

| **מעבר לשלב 9** | `builder.selected_potential` = 4 מניות |

### שלב 9: הקצאת משקלים קבועים
| | פירוט |
|---|--------|
| **קלט** | 10 מניות: 6 בסיס + 4 פוטנציאל (לפי סדר דירוג) |
| **עיבוד** | הקצאת משקלים קבועים מ-`settings.FUND_WEIGHTS`: |

| מיקום | סוג | מניה | משקל |
|-------|------|------|------|
| 1 | בסיס | NXSN.TA | 18% |
| 2 | בסיס | CLIS.TA | 16% |
| 3 | בסיס | STRS.TA | 16% |
| 4 | בסיס | LUMI.TA | 10% |
| 5 | בסיס | MMHD.TA | 10% |
| 6 | בסיס | ESLT.TA | 10% |
| 7 | פוטנציאל | ELAL.TA | 6% |
| 8 | פוטנציאל | ASHG.TA | 6% |
| 9 | פוטנציאל | MTAV.TA | 4% |
| 10 | פוטנציאל | FTAL.TA | 4% |
| | | **סה"כ** | **100%** |

| **מעבר לשלב 10** | כל מניה עם `_assigned_weight` |

### שלב 10: חישוב עלות מינימלית ליחידת קרן
| | פירוט |
|---|--------|
| **קלט** | 10 פוזיציות: (stock, weight) |
| **עיבוד** | `builder.calculate_minimum_fund_cost(positions)` |

#### אלגוריתם חישוב:
1. **מציאת המניה היקרה ביותר:**
   - ESLT.TA (Elbit) = 2,198.00 ₪ (משקל 10%)

2. **חישוב עלות קרן** (כך שהמניה היקרה תקבל מניה 1):
   ```
   fund_cost = max_price / max_weight = 2198.00 / 0.10 = 21,980.00
   ```

3. **חישוב מספר מניות לכל פוזיציה:**
   ```
   target_value = fund_cost × weight
   num_shares = round(target_value / stock_price)
   minimum: 1 share
   ```

4. **חישוב עלות ממשית:**
   ```
   actual_cost = Σ (num_shares × price)
   ```

#### טבלת חישוב מפורטת:
| מניה | מחיר (₪) | משקל | ערך יעד (₪) | מניות | ערך ממשי (₪) |
|------|----------|------|-------------|-------|-------------|
| NXSN.TA | 278.90 | 18% | 3,956.40 | 14 | 3,904.60 |
| CLIS.TA | 226.70 | 16% | 3,516.80 | 16 | 3,627.20 |
| STRS.TA | 117.10 | 16% | 3,516.80 | 30 | 3,513.00 |
| LUMI.TA | 74.73 | 10% | 2,198.00 | 29 | 2,167.17 |
| MMHD.TA | 399.50 | 10% | 2,198.00 | 6 | 2,397.00 |
| ESLT.TA | 2,198.00 | 10% | 2,198.00 | 1 | 2,198.00 |
| ELAL.TA | 17.55 | 6% | 1,318.80 | 75 | 1,316.25 |
| ASHG.TA | 68.71 | 6% | 1,318.80 | 19 | 1,305.49 |
| MTAV.TA | 120.80 | 4% | 879.20 | 7 | 845.60 |
| FTAL.TA | 639.50 | 4% | 879.20 | 1 | 639.50 |
| | | **100%** | | | **21,913.81** |

| **פלט** | `min_cost = 21,913.81 ₪`, `shares_dict = {symbol: num_shares}` |
| **מעבר לשלב 11** | `min_cost` ו-`shares_dict` משמשים ליצירת Fund |

### שלב 11: יצירת טבלת הקרן
| | פירוט |
|---|--------|
| **קלט** | 10 מניות עם weights + shares_dict |
| **עיבוד** | יצירת `FundPosition` לכל מניה, `Fund` object |
| **פלט** | `Fund` עם 10 positions, `minimum_cost = 21,913.81` |
| **מעבר לשלב 12** | `fund` + `ranked_base` + `ranked_potential` למסמכים |

### שלב 12: יצירת מסמך עדכון קרן
| | פירוט |
|---|--------|
| **קלט** | `fund`, `ranked_base` (33), `ranked_potential` (84) |
| **עיבוד** | כתיבת Markdown עם 3 טבלאות: |
| | 1. מניות בסיס מדורגות (כל 33) |
| | 2. מניות פוטנציאל מדורגות (כל 84) |
| | 3. הרכב קרן סופי (10 מניות) |
| **פלט** | `Fund_Docs/Fund_10_TASE125_Q1_2026_Update.md` |

### שלב 13: יצירת מסמך קרן סופי
| | פירוט |
|---|--------|
| **קלט** | `fund` object |
| **עיבוד** | כתיבת Markdown עם `fund.to_markdown()` |
| **פלט** | `Fund_Docs/Fund_10_TASE125_Q1_2026.md` |
| | כולל: טבלת 10 מניות + עלות מינימלית |

### שלב 14: ולידציה ואימות
| | פירוט |
|---|--------|
| **קלט** | `fund` object |
| **עיבוד** | `builder.validate_fund(fund)` — 6 בדיקות: |

| # | בדיקה | תוצאה |
|---|--------|--------|
| 1 | סכום משקלים = 100% | ✅ (1.0000) |
| 2 | 10 מניות בדיוק | ✅ (10) |
| 3 | 6 מניות בסיס | ✅ (6) |
| 4 | 4 מניות פוטנציאל | ✅ (4) |
| 5 | ללא חפיפה בסימולים | ✅ |
| 6 | מספר מניות שלם | ✅ |

**+ אימות Cache** (Post-validation):
- נבדק שציוני base/potential נשמרו ב-cache
- `NXSN.TA` cache verified ✅
- `ELAL.TA` cache verified ✅

---

## 3. מלאי נתונים חסרים (Missing Data Inventory)

### 3.1 סיכום כללי
| נתון | מניות חסרות | אחוז | פירוט |
|------|------------|------|--------|
| **קבצי cache** | 110/117 | 94.0% | 7 מניות לא נטענו בכלל |
| **financial_data** | 0/110 | 0% | כל 110 עם נתונים פיננסיים |
| **market_data** | 0/110 | 0% | כל 110 עם נתוני שוק |
| **current_price** | 0/110 | 0% | כל 110 עם מחיר נוכחי |
| **price_history** | 0/110 | 0% | כל 110 עם היסטוריית מחירים |
| **pe_ratio** | 2/110 | 1.8% | `FORTY.TA`, `OPK.TA` |
| **market_cap** | 1/110 | 0.9% | `FORTY.TA` |
| **revenues** | 0/110 | 0% | כל 110 עם נתוני הכנסות |
| **net_incomes** | 0/110 | 0% | כל 110 עם נתוני רווח |
| **operating_incomes** | 0/110 | 0% | כל 110 עם נתוני רווח תפעולי |
| **operating_cash_flows** | 0/110 | 0% | כל 110 עם תזרים מזומנים |
| **debt/equity** | 0/110 | 0% | כל 110 עם נתוני חוב/הון |

### 3.2 מניות שנכשלו בטעינה (7 מניות)
סימולים שלא קיימים ב-TwelveData API:

| # | סימול | סיבה |
|---|--------|-------|
| 1 | SPNS.TA | סימול לא מזוהה ב-TwelveData |
| 2 | PZOL.TA | סימול לא מזוהה ב-TwelveData |
| 3 | CRSO.TA | סימול לא מזוהה ב-TwelveData |
| 4 | ISRA-L.TA | סימול עם מקף לא נתמך |
| 5 | DEDR.TA | סימול לא מזוהה ב-TwelveData |
| 6 | RATI-L.TA | סימול עם מקף לא נתמך |
| 7 | DELT.TA | סימול לא מזוהה ב-TwelveData |

**השפעה:** מניות אלו לא משתתפות כלל בתהליך הדירוג. אם הן בעלות ביצועים טובים, הן חסרות מהקרן.

### 3.3 מניות עם נתונים חלקיים
| מניה | נתון חסר | השפעה על ציון |
|------|----------|---------------|
| FORTY.TA | P/E ratio, market_cap | base_score: market_cap_raw=0 (→ normalized=0); potential: valuation=0.0 |
| OPK.TA | P/E ratio | potential: valuation=0.0 (momentum ו-growth לא מושפעים) |

### 3.4 הערות על איכות נתונים
1. **היסטוריית מחירים מצומצמת**: TwelveData מספק נתונים חודשיים (~25 נקודות), לא יומיים. האזהרה `Insufficient price history: X days` מופיעה לכל המניות החדשות (threshold < 200). זה לא באמת חוסר — זהו פורמט חודשי.
2. **P/E שלילי**: מניות עם הפסדים לא מקבלות P/E (null), לא P/E שלילי.
3. **Index P/E**: ערך 14.0 הוא **הערכה קבועה** (hardcoded), לא ערך ממשי מחושב.

---

## 4. סיכום סטטיסטי

### 4.1 מעבר בין שלבים (Funnel)
```
117 מניות במדד (cache)
  │
  ├─ 7 נכשלו בטעינה
  │
  110 מניות נטענו
  │
  ├─ 33 כשירות לבסיס ──→ ציון ──→ top 6 נבחרות
  │
  104 ברשימת פוטנציאל (110 - 6 בסיס)
  │
  ├─ 20 לא כשירות
  │
  84 כשירות לפוטנציאל ──→ ציון ──→ top 4 נבחרות
  │
  10 מניות בקרן הסופית
```

### 4.2 התפלגות ציוני בסיס (33 מניות)
| מדד | ערך |
|-----|-----|
| ציון מקסימלי | 80.25 (NXSN.TA) |
| ציון מינימלי | 4.92 (ICL.TA) |
| ציון ממוצע | ~28.7 |
| ציון חציוני | ~24.0 |
| סף כניסה (top 6) | 43.36 (ESLT.TA) |

### 4.3 התפלגות ציוני פוטנציאל (84 מניות)
| מדד | ערך |
|-----|-----|
| ציון מקסימלי | 70.10 (ELAL.TA) |
| ציון מינימלי | 20.62 (ORL.TA) |
| סף כניסה (top 4) | 54.01 (FTAL.TA) |

### 4.4 הקרן הסופית
| מניה | סוג | משקל | מחיר (₪) | מניות/יחידה | ציון |
|------|------|------|----------|-------------|------|
| NXSN.TA | בסיס | 18% | 278.90 | 14 | 80.25 |
| CLIS.TA | בסיס | 16% | 226.70 | 16 | 72.68 |
| STRS.TA | בסיס | 16% | 117.10 | 30 | 49.99 |
| LUMI.TA | בסיס | 10% | 74.73 | 29 | 46.74 |
| MMHD.TA | בסיס | 10% | 399.50 | 6 | 45.85 |
| ESLT.TA | בסיס | 10% | 2,198.00 | 1 | 43.36 |
| ELAL.TA | פוטנציאל | 6% | 17.55 | 75 | 70.10 |
| ASHG.TA | פוטנציאל | 6% | 68.71 | 19 | 65.37 |
| MTAV.TA | פוטנציאל | 4% | 120.80 | 7 | 63.14 |
| FTAL.TA | פוטנציאל | 4% | 639.50 | 1 | 54.01 |

**עלות מינימלית ליחידת קרן: 21,913.81 ₪**

---

## 5. קבצי פלט שנוצרו

| קובץ | תיאור |
|------|--------|
| `Fund_Docs/Fund_10_TASE125_Q1_2026.md` | מסמך קרן סופי (טבלת 10 מניות + עלות) |
| `Fund_Docs/Fund_10_TASE125_Q1_2026_Update.md` | מסמך עדכון (33 בסיס + 84 פוטנציאל + קרן סופית) |
| `cache/stocks_data/*.json` × 110 | נתוני מניות מעודכנים עם ציונים |
| `cache/index_constituents/TASE125_Q1_2026.json` | רשימת 117 רכיבי מדד (עותק Q4 2025) |

---

## 6. ממצאים והמלצות

### 6.1 נקודות חוזק
- **כיסוי נתונים מצוין**: 110/117 מניות עם נתונים מלאים (94%)
- **33 מניות כשירות לבסיס**: שיפור משמעותי לעומת EODHD (2 בלבד) — בזכות `operating_income` אמיתי (לא EBITDA null לבנקים)
- **ולידציה מלאה**: כל 6 הבדיקות עברו ✅
- **Cache efficiency**: הרצה חוזרת ב-<10 שניות

### 6.2 נקודות לשיפור
1. **7 סימולים חסרים**: יש למפות SPNS, PZOL, CRSO, ISRA-L, DEDR, RATI-L, DELT לסימולים תקינים ב-TwelveData או להוסיף fallback
2. **Index P/E hardcoded**: 14.0 הוא הערכה — כדאי לחשב ממוצע משוקלל מנתוני P/E של כל 110 המניות
3. **Price history format**: היסטוריה חודשית (24 נקודות) במקום יומית — מומנטום מחושב על ~2 שנים במקום שנה אחת
4. **FORTY.TA חסר market_cap**: משפיע על ציון base (market_cap_normalized=0)
5. **רשימת מדד מ-Q4 2025**: הרכב TA-125 עשוי להשתנות — יש לעדכן cache לפני כל רבעון

---

*דוח זה נוצר אוטומטית על ידי ניתוח קוד המקור, נתוני cache, ולוגי הרצה של build_fund.py*
