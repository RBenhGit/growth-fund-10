# -*- coding: utf-8 -*-
import sys
import requests
import json
import time
from datetime import datetime, timedelta
import pandas as pd

# Fix Windows console encoding for Hebrew text
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# הגדרות API
API_KEY = "0acd9c29-5514-42fe-978e-41ff565b09e1"
BASE_URL = "https://datahubist.tase.co.il"

headers = {
    "accept": "application/json",
    "accept-language": "he-IL",
    "apikey": f"Apikey {API_KEY}"
}

def rate_limit_wait():
    """המתנה בין קריאות למניעת חריגה מ-rate limit"""
    time.sleep(0.3)  # 10 קריאות לשניתיים = המתנה של 0.2 שניות מינימום

def get_ta125_companies():
    """מושך את רשימת החברות במדד ת"א 125"""
    endpoint = f"{BASE_URL}/api/Index/IndexComponents"
    params = {"indexId": 137}
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"שגיאה בשליפת רשימת חברות: {e}")
        return None

def get_company_financial_data(security_id, years=5):
    """
    מושך נתונים פיננסיים לחברה ספציפית
    
    Args:
        security_id: מזהה נייר הערך
        years: מספר שנים לשליפה
    """
    financial_data = {
        'security_id': security_id,
        'income_statements': [],
        'balance_sheets': [],
        'cash_flows': [],
        'key_metrics': {}
    }
    
    # חישוב טווח תאריכים
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)
    
    try:
        # 1. דוח רווח והפסד (Income Statement)
        print(f"  מושך דוח רווח והפסד עבור {security_id}...")
        income_endpoint = f"{BASE_URL}/api/FinancialStatements/IncomeStatement"
        income_params = {
            "securityId": security_id,
            "fromDate": start_date.strftime("%Y-%m-%d"),
            "toDate": end_date.strftime("%Y-%m-%d")
        }
        rate_limit_wait()
        income_response = requests.get(income_endpoint, headers=headers, params=income_params)
        if income_response.status_code == 200:
            financial_data['income_statements'] = income_response.json()
        
        # 2. מאזן (Balance Sheet)
        print(f"  מושך מאזן עבור {security_id}...")
        balance_endpoint = f"{BASE_URL}/api/FinancialStatements/BalanceSheet"
        balance_params = {
            "securityId": security_id,
            "fromDate": start_date.strftime("%Y-%m-%d"),
            "toDate": end_date.strftime("%Y-%m-%d")
        }
        rate_limit_wait()
        balance_response = requests.get(balance_endpoint, headers=headers, params=balance_params)
        if balance_response.status_code == 200:
            financial_data['balance_sheets'] = balance_response.json()
        
        # 3. תזרים מזומנים (Cash Flow)
        print(f"  מושך תזרים מזומנים עבור {security_id}...")
        cashflow_endpoint = f"{BASE_URL}/api/FinancialStatements/CashFlow"
        cashflow_params = {
            "securityId": security_id,
            "fromDate": start_date.strftime("%Y-%m-%d"),
            "toDate": end_date.strftime("%Y-%m-%d")
        }
        rate_limit_wait()
        cashflow_response = requests.get(cashflow_endpoint, headers=headers, params=cashflow_params)
        if cashflow_response.status_code == 200:
            financial_data['cash_flows'] = cashflow_response.json()
        
        # 4. מדדים פיננסיים מרכזיים
        financial_data['key_metrics'] = extract_key_metrics(financial_data)
        
        return financial_data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("  חריגה ממכסת קריאות - ממתין 5 שניות...")
            time.sleep(5)
            return get_company_financial_data(security_id, years)
        else:
            print(f"  שגיאה בשליפת נתונים פיננסיים: {e}")
            return financial_data
    except Exception as e:
        print(f"  שגיאה: {e}")
        return financial_data

def extract_key_metrics(financial_data):
    """מחלץ מדדים פיננסיים מרכזיים"""
    metrics = {
        'revenue_5y': [],
        'net_income_5y': [],
        'operating_income_5y': [],
        'cash_flow_5y': [],
        'total_debt': None,
        'total_equity': None,
        'debt_to_equity': None
    }
    
    try:
        # חילוץ הכנסות ורווח נקי מדוחות רווח והפסד
        for statement in financial_data.get('income_statements', []):
            year = statement.get('year') or statement.get('period')
            
            revenue = statement.get('totalRevenue') or statement.get('revenue')
            if revenue:
                metrics['revenue_5y'].append({'year': year, 'value': revenue})
            
            net_income = statement.get('netIncome') or statement.get('profitLoss')
            if net_income:
                metrics['net_income_5y'].append({'year': year, 'value': net_income})
            
            operating_income = statement.get('operatingIncome') or statement.get('operatingProfit')
            if operating_income:
                metrics['operating_income_5y'].append({'year': year, 'value': operating_income})
        
        # חילוץ תזרים מזומנים
        for cf_statement in financial_data.get('cash_flows', []):
            year = cf_statement.get('year') or cf_statement.get('period')
            
            operating_cf = cf_statement.get('operatingActivities') or cf_statement.get('cashFromOperations')
            if operating_cf:
                metrics['cash_flow_5y'].append({'year': year, 'value': operating_cf})
        
        # חילוץ חוב והון מהמאזן האחרון
        if financial_data.get('balance_sheets'):
            latest_balance = financial_data['balance_sheets'][0]
            
            metrics['total_debt'] = latest_balance.get('totalDebt') or latest_balance.get('liabilities')
            metrics['total_equity'] = latest_balance.get('totalEquity') or latest_balance.get('equity')
            
            if metrics['total_debt'] and metrics['total_equity'] and metrics['total_equity'] != 0:
                metrics['debt_to_equity'] = (metrics['total_debt'] / metrics['total_equity']) * 100
        
        # מיון לפי שנה
        metrics['revenue_5y'].sort(key=lambda x: x['year'], reverse=True)
        metrics['net_income_5y'].sort(key=lambda x: x['year'], reverse=True)
        metrics['operating_income_5y'].sort(key=lambda x: x['year'], reverse=True)
        metrics['cash_flow_5y'].sort(key=lambda x: x['year'], reverse=True)
        
    except Exception as e:
        print(f"  שגיאה בחילוץ מדדים: {e}")
    
    return metrics

def calculate_growth_rates(financial_data):
    """מחשב שיעורי צמיחה"""
    metrics = financial_data.get('key_metrics', {})
    growth_rates = {}
    
    try:
        # צמיחה בהכנסות
        revenue_list = metrics.get('revenue_5y', [])
        if len(revenue_list) >= 2:
            latest = revenue_list[0]['value']
            oldest = revenue_list[-1]['value']
            years = len(revenue_list) - 1
            if oldest > 0:
                growth_rates['revenue_cagr'] = ((latest / oldest) ** (1/years) - 1) * 100
        
        # צמיחה ברווח נקי
        income_list = metrics.get('net_income_5y', [])
        if len(income_list) >= 2:
            latest = income_list[0]['value']
            oldest = income_list[-1]['value']
            years = len(income_list) - 1
            if oldest > 0:
                growth_rates['net_income_cagr'] = ((latest / oldest) ** (1/years) - 1) * 100
        
    except Exception as e:
        print(f"  שגיאה בחישוב צמיחה: {e}")
    
    return growth_rates

def check_eligibility_criteria(financial_data):
    """בדיקת קריטריוני כשירות לקרן (לפי מסמך האפיון)"""
    metrics = financial_data.get('key_metrics', {})
    criteria = {
        'profitable_5y': False,
        'operating_profit_4of5': False,
        'positive_cash_flow': False,
        'debt_ratio_ok': False,
        'eligible': False
    }
    
    try:
        # 1. רווחיות יציבה - רווח נקי חיובי ב-5 השנים האחרונות
        net_income = metrics.get('net_income_5y', [])
        if len(net_income) >= 5:
            positive_years = sum(1 for item in net_income[:5] if item['value'] > 0)
            criteria['profitable_5y'] = (positive_years == 5)
        
        # 2. יציבות תפעולית - רווח תפעולי חיובי ב-4 מתוך 5 שנים
        operating_income = metrics.get('operating_income_5y', [])
        if len(operating_income) >= 5:
            positive_years = sum(1 for item in operating_income[:5] if item['value'] > 0)
            criteria['operating_profit_4of5'] = (positive_years >= 4)
        
        # 3. תזרים מזומנים חיובי במרבית השנים
        cash_flow = metrics.get('cash_flow_5y', [])
        if len(cash_flow) >= 3:
            positive_years = sum(1 for item in cash_flow if item['value'] > 0)
            criteria['positive_cash_flow'] = (positive_years >= len(cash_flow) / 2)
        
        # 4. יחס חוב/הון מתחת ל-60%
        debt_ratio = metrics.get('debt_to_equity')
        if debt_ratio is not None:
            criteria['debt_ratio_ok'] = (debt_ratio < 60)
        
        # בדיקה כוללת
        criteria['eligible'] = all([
            criteria['profitable_5y'],
            criteria['operating_profit_4of5'],
            criteria['positive_cash_flow'],
            criteria['debt_ratio_ok']
        ])
        
    except Exception as e:
        print(f"  שגיאה בבדיקת כשירות: {e}")
    
    return criteria

def get_all_companies_financial_data():
    """מושך נתונים פיננסיים לכל חברות המדד"""
    print("שלב 1: מושך רשימת חברות מדד ת\"א 125...\n")
    companies = get_ta125_companies()
    
    if not companies:
        print("לא הצלחנו לשלוף את רשימת החברות")
        return None
    
    print(f"נמצאו {len(companies)} חברות\n")
    print("=" * 80)
    print("שלב 2: מושך נתונים פיננסיים...\n")
    
    results = []
    
    for i, company in enumerate(companies, 1):
        company_name = company.get('companyName', 'N/A')
        security_id = company.get('securityId')
        
        print(f"{i}/{len(companies)}: {company_name} ({security_id})")
        
        if not security_id:
            print("  ⚠️ חסר מזהה נייר ערך - מדלג\n")
            continue
        
        # שליפת נתונים פיננסיים
        financial_data = get_company_financial_data(security_id)
        
        # חישוב שיעורי צמיחה
        growth_rates = calculate_growth_rates(financial_data)
        
        # בדיקת כשירות
        eligibility = check_eligibility_criteria(financial_data)
        
        # איחוד הכל
        company_full_data = {
            'company_info': company,
            'financial_data': financial_data,
            'growth_rates': growth_rates,
            'eligibility': eligibility
        }
        
        results.append(company_full_data)
        
        # הצגת סיכום
        print(f"  ✓ הושלם")
        print(f"  כשיר לקרן: {'✓ כן' if eligibility['eligible'] else '✗ לא'}")
        if growth_rates.get('revenue_cagr'):
            print(f"  צמיחת הכנסות: {growth_rates['revenue_cagr']:.2f}%")
        print()
        
        # הפסקה כל 20 חברות למניעת עומס
        if i % 20 == 0:
            print("⏸️ הפסקה קצרה...")
            time.sleep(3)
    
    return results

def create_summary_report(results):
    """יצירת דוח סיכום"""
    print("\n" + "=" * 80)
    print("דוח סיכום - מניות כשירות לקרן הבסיס")
    print("=" * 80 + "\n")
    
    eligible_companies = [r for r in results if r['eligibility']['eligible']]
    
    print(f"סה\"כ חברות שנבדקו: {len(results)}")
    print(f"חברות כשירות לקרן: {len(eligible_companies)}")
    print(f"אחוז כשירות: {(len(eligible_companies)/len(results)*100):.1f}%\n")
    
    if eligible_companies:
        print("חברות כשירות עם צמיחה הגבוהה ביותר:")
        print("-" * 80)
        
        # מיון לפי צמיחת הכנסות
        sorted_by_growth = sorted(
            [c for c in eligible_companies if c['growth_rates'].get('revenue_cagr')],
            key=lambda x: x['growth_rates']['revenue_cagr'],
            reverse=True
        )
        
        for i, company in enumerate(sorted_by_growth[:10], 1):
            name = company['company_info'].get('companyName', 'N/A')
            revenue_growth = company['growth_rates'].get('revenue_cagr', 0)
            income_growth = company['growth_rates'].get('net_income_cagr', 0)
            
            print(f"{i}. {name}")
            print(f"   צמיחת הכנסות: {revenue_growth:.2f}%")
            if income_growth:
                print(f"   צמיחת רווח נקי: {income_growth:.2f}%")
            print()

def save_results(results, filename_prefix="ta125_financial"):
    """שמירת תוצאות"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # שמירה ל-JSON
    json_filename = f"{filename_prefix}_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"✓ נשמר ל-JSON: {json_filename}")
    
    # שמירה ל-Excel (אם pandas מותקן)
    try:
        excel_data = []
        for result in results:
            company = result['company_info']
            metrics = result['financial_data'].get('key_metrics', {})
            growth = result['growth_rates']
            eligibility = result['eligibility']
            
            row = {
                'שם חברה': company.get('companyName'),
                'סימול': company.get('securityId'),
                'שווי שוק': company.get('marketCap'),
                'כשיר לקרן': 'כן' if eligibility['eligible'] else 'לא',
                'צמיחת הכנסות (%)': growth.get('revenue_cagr'),
                'צמיחת רווח נקי (%)': growth.get('net_income_cagr'),
                'יחס חוב/הון (%)': metrics.get('debt_to_equity'),
                'רווחיות 5 שנים': 'כן' if eligibility['profitable_5y'] else 'לא',
                'רווח תפעולי 4/5': 'כן' if eligibility['operating_profit_4of5'] else 'לא',
            }
            excel_data.append(row)
        
        df = pd.DataFrame(excel_data)
        excel_filename = f"{filename_prefix}_{timestamp}.xlsx"
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        print(f"✓ נשמר ל-Excel: {excel_filename}")
        
    except ImportError:
        print("⚠️ pandas לא מותקן - דלג על יצירת Excel")
    except Exception as e:
        print(f"⚠️ שגיאה בשמירת Excel: {e}")

if __name__ == "__main__":
    print("=" * 80)
    print("מערכת ניתוח פיננסי - מדד ת\"א 125")
    print("=" * 80 + "\n")
    
    # שליפת כל הנתונים
    results = get_all_companies_financial_data()
    
    if results:
        # יצירת דוח סיכום
        create_summary_report(results)
        
        # שמירת תוצאות
        print("\n" + "=" * 80)
        print("שומר תוצאות...")
        save_results(results)
        
        print("\n✓ התהליך הושלם בהצלחה!")
    else:
        print("\n✗ התהליך נכשל")