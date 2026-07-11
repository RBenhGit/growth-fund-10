# Growth Fund 10 — Changelog

מעקב אחר שינויי הרכב הקרן לאורך רבעונים.

---

### [2026-07-10] תיקוני מתודולוגיה ולוגיקת ניקוד (methodology & scoring fixes)

שינויי קוד המשפיעים על כשירות מניות וניקוד. **הרצת בנייה מלאה או עדכון הבא עשויה לשנות הרכב** לעומת הצפוי מהגרסה הקודמת.

**תיקוני נכונות (משנים הרכב):**
- **כשירות אינה "מנעול חד-כיווני" יותר** — `check_base_eligibility`/`check_potential_eligibility` מאפסים את דגל הכשירות ל-`False` בתחילת כל בדיקה. בעדכון הרבעוני, מניה מ-cache שסומנה ככשירה ושנתוני ה-LTM המעודכנים שלה נכשלים בקריטריון (הפסד נקי, חוב/הון מעל 60%) — מאבדת כשירות במקום להישאר בקרן עד הבנייה המלאה הבאה. (`models/stock.py`)
- **מומנטום = חלון ~12 חודשים עקבי** — `calculate_momentum` מחפש כעת את המחיר הקרוב ביותר ל-(תאריך תצפית אחרון − days_ago) במקום "תשואה מאז המחיר הישן ביותר". קודם החלון השתנה ממניה למניה וחפף לגורם הצמיחה. (`models/financial_data.py`)
- **שימור חוב/הון ב-LTM** — כאשר המאזן הרבעוני אינו מחזיר חוב/הון, ערכי ה-cache השנתיים נשמרים במקום להתאפס ל-0.0 (איפוס גרם ל-`debt_to_equity_ratio=None` ולמעבר שקט של סף החוב). (`utils/ltm_calculator.py`)
- **הון עצמי שלילי/אפס נדחה** בכשירות בסיס (קודם עבר בשקט דרך `debt_to_equity_ratio=None`). (`models/stock.py`)
- **נדרשת היסטוריית הכנסות של 5 שנים** לכשירות בסיס, כדי שצמיחת ההכנסות בניקוד תהיה אמיתית ולא 0.0 מדומה. (`models/stock.py`)
- **מאגר הפוטנציאל בעדכון תואם לבנייה המלאה** — מניה כשירה-לבסיס שאינה נבחרת ל-6 נשארת מועמדת פוטנציאל (תוקן `elif`→`if`). (`fund_builder/updater.py`)

**תיקוני עקביות / ניקיון:**
- `get_base_positions`/`get_potential_positions` סוננו לפי תוויות אנגליות שגויות; תוקן לעברית ("בסיס"/"פוטנציאל"). (`models/fund.py`)
- הוסר קוד מת (`calculate_lcm`) ותוקנו הערות מטעות (CAGR "מונע עיוות מאירועים חד-פעמיים" — לא נכון; "LTM מוסיף שנה" — למעשה דורס את השנה האחרונה). (`fund_builder/builder.py`)
- עודכנו CLAUDE.md, README.md וכלי `demonstrate_calculations.py` לשקף את המתודולוגיה בפועל, כולל מסגור **"Quality Growth at Scale"** לסל הבסיס (80% מההון).

---

### [2025-12-17] Fund_10_SP500_Q4_2025 — בנייה מלאה (baseline)

- **בנייה מלאה** — הרכב ראשוני
- 10 מניות נבחרו (6 בסיס + 4 פוטנציאל)

---

### [2025-12-17] Fund_10_TASE125_Q4_2025 — בנייה מלאה (baseline)

- **בנייה מלאה** — הרכב ראשוני
- 10 מניות נבחרו (6 בסיס + 4 פוטנציאל)

---

### [2026-02-11] Fund_10_SP500_Q1_2026 — בנייה מלאה

- **בנייה מלאה** — הרכב ראשוני
- NVDA (18%), CRM (16%), GOOG (16%), MSFT (10%), TTD (10%), AMD (10%)
- COIN (6%), MU (6%), SMCI (4%), VST (4%)

**עלות מינימלית:** $4,258.65

---

### [2026-02-10] Fund_10_TASE125_Q1_2026 — בנייה מלאה

- **בנייה מלאה** — הרכב ראשוני
- NXSN (18%), CLIS (16%), STRS (16%), LUMI (10%), MMHD (10%), POLI (10%)
- AURA (6%), ELAL (6%), ASHG (4%), TMRP (4%)

**עלות מינימלית:** ₪485,540.00

---

### [2026-02-14] Fund_10_SP500_Q1_2026 — 3 מניות נוספו, 3 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q1_2026 (2026-02-11)

- **+** TKO Group Holdings, Inc. (TKO.US) — בסיס, 10%, ציון 21.96
- **+** Seagate Technology PLC (STX.US) — פוטנציאל, 6%, ציון 51.48
- **+** Targa Resources Inc (TRGP.US) — פוטנציאל, 4%, ציון 50.15
- **-** Trade Desk Inc (TTD.US) — בסיס, 10%
- **-** Coinbase Global Inc (COIN.US) — פוטנציאל, 6%
- **-** Vistra Energy Corp (VST.US) — פוטנציאל, 4%

**עלות מינימלית:** $7,023.32

---
### [2026-02-14] Fund_10_TASE125_Q1_2026 — 5 מניות נוספו, 5 מניות הוסרו

**עדכון מ:** Fund_10_TASE125_Q1_2026 (2026-02-10)

- **+** Elbit Systems Ltd (ESLT.TA) — בסיס, 16%, ציון 46.97
- **+** Nova Ltd (NVMI.TA) — בסיס, 10%, ציון 39.27
- **+** MEITAV INVESTMENTS HOUSE R1 RIGHTS (MTAV.TA) — פוטנציאל, 6%, ציון 92.40
- **+** Harel Insurance Investments & Financial Services Ltd (HARL.TA) — פוטנציאל, 6%, ציון 73.72
- **+** The Phoenix Holdings Ltd. (PHOE.TA) — פוטנציאל, 4%, ציון 62.42
- **-** Strauss Group (STRS.TA) — בסיס, 16%
- **-** Menora Miv Hld (MMHD.TA) — בסיס, 10%
- **-** Aura Investments Ltd (AURA.TA) — פוטנציאל, 6%
- **-** El Al Israel Airlines Ltd (ELAL.TA) — פוטנציאל, 6%
- **-** Ashtrom Group Ltd (ASHG.TA) — פוטנציאל, 4%

**עלות מינימלית:** ₪1,295,376.00

---
### [2026-02-16] Fund_10_TASE125_Q1_2026 — 4 מניות נוספו, 4 מניות הוסרו

**עדכון מ:** Fund_10_TASE125_Q1_2026 (2026-02-16)

- **+** Elbit Systems Ltd (ESLT.TA) — בסיס, 16%, ציון 46.97
- **+** MEITAV INVESTMENTS HOUSE R1 RIGHTS (MTAV.TA) — פוטנציאל, 6%, ציון 92.40
- **+** Harel Insurance Investments & Financial Services Ltd (HARL.TA) — פוטנציאל, 6%, ציון 73.72
- **+** The Phoenix Holdings Ltd. (PHOE.TA) — פוטנציאל, 4%, ציון 62.42
- **-** Strauss Group (STRS.TA) — בסיס, 16%
- **-** Aura Investments Ltd (AURA.TA) — פוטנציאל, 6%
- **-** El Al Israel Airlines Ltd (ELAL.TA) — פוטנציאל, 6%
- **-** Ashtrom Group Ltd (ASHG.TA) — פוטנציאל, 4%

**עלות מינימלית:** ₪1,304,596.00

---
### [2026-02-16] Fund_10_SP500_Q1_2026 — 2 מניות נוספו, 2 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q1_2026 (2026-02-16)

- **+** TKO Group Holdings, Inc. (TKO.US) — בסיס, 10%, ציון 20.91
- **+** EQT Corporation (EQT.US) — פוטנציאל, 6%, ציון 49.45
- **-** Trade Desk Inc (TTD.US) — בסיס, 10%
- **-** Incyte Corporation (INCY.US) — פוטנציאל, 6%

**עלות מינימלית:** $7,076.14

---
### [2026-04-10] Fund_10_SP500_Q2_2026 — 5 מניות נוספו, 5 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q1_2026 (2026-03-23)

- **+** News Corp B (NWS.US) — בסיס, 10%, ציון 40.03
- **+** News Corp A (NWSA.US) — בסיס, 10%, ציון 40.03
- **+** Seagate Technology PLC (STX.US) — פוטנציאל, 6%, ציון 56.24
- **+** EQT Corporation (EQT.US) — פוטנציאל, 4%, ציון 50.19
- **+** Super Micro Computer Inc (SMCI.US) — פוטנציאל, 4%, ציון 48.73
- **-** Alphabet Inc Class A (GOOGL.US) — בסיס, 16%
- **-** Microsoft Corporation (MSFT.US) — בסיס, 10%
- **-** Incyte Corporation (INCY.US) — פוטנציאל, 6%
- **-** Micron Technology Inc (MU.US) — פוטנציאל, 6%
- **-** Palantir Technologies Inc. (PLTR.US) — פוטנציאל, 4%

**עלות מינימלית:** $8,393.95

---
### [2026-04-11] Fund_10_SP500_Q2_2026 — 3 מניות נוספו, 3 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-04-11)

- **+** Booking Holdings Inc (BKNG.US) — בסיס, 10%, ציון 31.34
- **+** Broadcom Inc (AVGO.US) — פוטנציאל, 6%, ציון 54.97
- **+** Super Micro Computer Inc (SMCI.US) — פוטנציאל, 4%, ציון 51.76
- **-** Alphabet Inc Class A (GOOGL.US) — בסיס, 16%
- **-** Microsoft Corporation (MSFT.US) — בסיס, 10%
- **-** Palantir Technologies Inc. (PLTR.US) — פוטנציאל, 6%

**עלות מינימלית:** $10,054.29

---
### [2026-04-11] Fund_10_SP500_Q2_2026 — 3 מניות נוספו, 3 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-04-11)

- **+** Booking Holdings Inc (BKNG.US) — בסיס, 10%, ציון 31.34
- **+** Super Micro Computer Inc (SMCI.US) — פוטנציאל, 4%, ציון 50.67
- **+** Broadcom Inc (AVGO.US) — פוטנציאל, 4%, ציון 48.16
- **-** Alphabet Inc Class A (GOOGL.US) — בסיס, 16%
- **-** Microsoft Corporation (MSFT.US) — בסיס, 10%
- **-** Palantir Technologies Inc. (PLTR.US) — פוטנציאל, 6%

**עלות מינימלית:** $6,665.98

---
### [2026-04-11] Fund_10_TASE125_Q2_2026 — 1 מניות נוספו, 1 מניות הוסרו

**עדכון מ:** Fund_10_TASE125_Q2_2026 (2026-04-11)

- **+** Turpaz Industries Ltd (TRPZ.TA) — בסיס, 10%, ציון 28.45
- **-** Tower Semiconductor Ltd (TSEM.TA) — בסיס, 10%

**עלות מינימלית:** ₪1,727,162.00

---
### [2026-04-29] Fund_10_SP500_Q2_2026 — 4 מניות נוספו, 4 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-04-29)

- **+** Welltower Inc (WELL.US) — בסיס, 10%, ציון 55.19
- **+** Applovin Corp (APP.US) — פוטנציאל, 6%, ציון 87.06
- **+** Palantir Technologies Inc. (PLTR.US) — פוטנציאל, 6%, ציון 81.76
- **+** Merck & Company Inc (MRK.US) — פוטנציאל, 4%, ציון 77.65
- **-** Transdigm Group Incorporated (TDG.US) — בסיס, 10%
- **-** Royal Caribbean Cruises Ltd (RCL.US) — פוטנציאל, 6%
- **-** Progressive Corp (PGR.US) — פוטנציאל, 6%
- **-** Leidos Holdings Inc (LDOS.US) — פוטנציאל, 4%

**עלות מינימלית:** $7,010.75

---
### [2026-05-03] Fund_10_TASE125_Q2_2026 — 2 מניות נוספו, 2 מניות הוסרו

**עדכון מ:** Fund_10_TASE125_Q2_2026 (2026-05-03)

- **+** One Software Technologies Ltd (ONE.TA) — בסיס, 10%, ציון 67.78
- **+** MEITAV INVESTMENTS HOUSE R1 RIGHTS (MTAV.TA) — פוטנציאל, 6%, ציון 90.00
- **-** Turpaz Industries Ltd (TRPZ.TA) — בסיס, 10%
- **-** The Phoenix Holdings Ltd. (PHOE.TA) — פוטנציאל, 4%

**עלות מינימלית:** ₪2,463,099.00

---
### [2026-05-03] Fund_10_TASE125_Q2_2026 — ללא שינויי הרכב

**עדכון מ:** Fund_10_TASE125_Q2_2026 (2026-05-03)

- ללא שינויים בהרכב

**עלות מינימלית:** ₪2,463,099.00

---
### [2026-05-04] Fund_10_SP500_Q2_2026 — 1 מניות נוספו, 1 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-04-29)

- **+** Eli Lilly and Company (LLY.US) — פוטנציאל, 4%, ציון 69.41
- **-** Cardinal Health Inc (CAH.US) — פוטנציאל, 4%

**עלות מינימלית:** $23,943.42

---
### [2026-05-04] Fund_10_SP500_Q2_2026 — ללא שינויי הרכב

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-05-04)

- ללא שינויים בהרכב

**עלות מינימלית:** $23,943.42

---
### [2026-05-04] Fund_10_SP500_Q2_2026 — ללא שינויי הרכב

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-05-04)

- ללא שינויים בהרכב

**עלות מינימלית:** $23,943.42

---
### [2026-05-04] Fund_10_SP500_Q2_2026 — ללא שינויי הרכב

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-05-04)

- ללא שינויים בהרכב

**עלות מינימלית:** $23,943.42

---
### [2026-05-07] Fund_10_TASE125_Q2_2026 — ללא שינויי הרכב

**עדכון מ:** Fund_10_TASE125_Q2_2026 (2026-05-03)

- ללא שינויים בהרכב

**עלות מינימלית:** ₪2,422,225.00

---
### [2026-05-07] Fund_10_SP500_Q2_2026 — ללא שינויי הרכב

**עדכון מ:** Fund_10_SP500_Q2_2026 (2026-05-04)

- ללא שינויים בהרכב

**עלות מינימלית:** $24,446.23

---
### [2026-07-11] Fund_10_TASE125_Q3_2026 — 2 מניות נוספו, 2 מניות הוסרו

**עדכון מ:** Fund_10_TASE125_Q3_2026 (2026-07-10)

- **+** IBI Inv House (IBI.TA) — בסיס, 16%, ציון 76.17
- **+** Mega Or (MGOR.TA) — פוטנציאל, 4%, ציון 90.86
- **-** Bank Hapoalim (POLI.TA) — בסיס, 18%
- **-** Menora Miv Hld (MMHD.TA) — פוטנציאל, 4%

**עלות מינימלית:** ₪2,319,929.00

---
### [2026-07-11] Fund_10_SP500_Q3_2026 — 4 מניות נוספו, 4 מניות הוסרו

**עדכון מ:** Fund_10_SP500_Q3_2026 (2026-07-11)

- **+** Welltower Inc (WELL.US) — בסיס, 10%, ציון 64.82
- **+** Merck & Company Inc (MRK.US) — פוטנציאל, 6%, ציון 92.20
- **+** Cardinal Health Inc (CAH.US) — פוטנציאל, 4%, ציון 87.32
- **+** Eli Lilly and Company (LLY.US) — פוטנציאל, 4%, ציון 81.95
- **-** Howmet Aerospace Inc (HWM.US) — בסיס, 10%
- **-** Palantir Technologies Inc. (PLTR.US) — פוטנציאל, 6%
- **-** Applovin Corp (APP.US) — פוטנציאל, 4%
- **-** Corning Incorporated (GLW.US) — פוטנציאל, 4%

**עלות מינימלית:** $29,548.77

---
