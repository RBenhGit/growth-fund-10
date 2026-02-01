# -*- coding: utf-8 -*-
import sys
import requests
import json

# Fix Windows console encoding for Hebrew text
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# הגדרות API
API_KEY = "ff1640b6-1cb7-4e60-b252-dc5ce21ea817"  # יש להחליף במפתח ה-API שלך
BASE_URL = "https://datahubist.tase.co.il"

# Headers עם authentication
headers = {
    "accept": "application/json",
    "accept-language": "he-IL",
    "apikey": f"Apikey {API_KEY}"
}

def get_ta125_companies():
    """
    מושך את רשימת החברות במדד ת"א 125
    """
    # Endpoint לקבלת רכיבי מדד
    # מספר המדד של ת"א 125 הוא 142
    endpoint = f"{BASE_URL}/api/Index/IndexComponents"
    
    params = {
        "indexId": 142  # מדד ת"א 125
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"נמצאו {len(data)} חברות במדד ת\"א 125\n")
        print("=" * 80)
        
        # הצגת הנתונים
        for i, company in enumerate(data, 1):
            print(f"{i}. {company.get('companyName', 'N/A')}")
            print(f"   סימול: {company.get('securityId', 'N/A')}")
            print(f"   שווי שוק: {company.get('marketCap', 'N/A')}")
            print(f"   משקל במדד: {company.get('weight', 'N/A')}%")
            print("-" * 80)
        
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("שגיאת הרשאה - בדוק שמפתח ה-API תקין")
        elif e.response.status_code == 429:
            print("חריגה ממכסת הקריאות - המתן מעט ונסה שוב")
        else:
            print(f"שגיאת HTTP: {e}")
        return None
        
    except Exception as e:
        print(f"שגיאה: {e}")
        return None

def save_to_file(data, filename="ta125_companies.json"):
    """
    שמירת הנתונים לקובץ JSON
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nהנתונים נשמרו בהצלחה לקובץ: {filename}")
    except Exception as e:
        print(f"שגיאה בשמירת הקובץ: {e}")

if __name__ == "__main__":
    print("מושך נתוני חברות מדד ת\"א 125...\n")
    
    companies = get_ta125_companies()
    
    if companies:
        # שמירה לקובץ
        save_to_file(companies)
        
        # סטטיסטיקות בסיסיות
        print("\n" + "=" * 80)
        print("סטטיסטיקות:")
        print(f"סה\"כ חברות: {len(companies)}")