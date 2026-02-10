# -*- coding: utf-8 -*-
"""
Test TASE Data Hub API - GetIndexComponent endpoint
Tests different auth header formats and endpoints.
"""
import sys
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(override=True)

API_KEY = os.getenv("TASE_DATA_HUB_API_KEY", "")

if not API_KEY:
    print("ERROR: TASE_DATA_HUB_API_KEY is empty in .env")
    sys.exit(1)

print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
print()

now = datetime.now()

# All combinations to try
HOSTS = [
    "https://datahubapi.tase.co.il",
    "https://datawise.tase.co.il",
]

PATHS = [
    "/api/Index/IndexComponents?indexId=142",
    "/api/Index/IndexComponents?indexId=137",
    f"/v1/basic-indices/index-components-basic/142/{now.year}/{now.month}/{now.day}",
    f"/v1/basic-indices/index-components-basic/137/{now.year}/{now.month}/{now.day}",
    "/v1/basic-indices/index-components-basic/142",
    "/v1/basic-indices/index-components-basic/137",
]

# Different auth header formats seen in the wild
AUTH_FORMATS = [
    ("apikey", f"Apikey {API_KEY}"),
    ("apikey", API_KEY),
    ("Authorization", f"Bearer {API_KEY}"),
    ("Authorization", f"Apikey {API_KEY}"),
    ("Ocp-Apim-Subscription-Key", API_KEY),
]

success_found = False

for host in HOSTS:
    for auth_name, auth_value in AUTH_FORMATS:
        if success_found:
            break

        headers = {
            "accept": "application/json",
            "accept-language": "he-IL",
            auth_name: auth_value,
        }

        auth_label = f"{auth_name}: {auth_value[:30]}..."

        for path in PATHS:
            url = f"{host}{path}"
            try:
                response = requests.get(url, headers=headers, timeout=10)

                # Only print interesting results (not 404s)
                if response.status_code in [200, 201]:
                    content = response.text
                    if content and content.strip() and content.strip() != "[]":
                        try:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                print(f"SUCCESS!")
                                print(f"  URL:  {url}")
                                print(f"  Auth: {auth_label}")
                                print(f"  Status: {response.status_code}")
                                print(f"  Items: {len(data)}")
                                print(f"  Keys: {list(data[0].keys())}")
                                print(f"  Sample:\n{json.dumps(data[0], ensure_ascii=False, indent=4)}")
                                print(f"\n  Last item:\n{json.dumps(data[-1], ensure_ascii=False, indent=4)}")
                                success_found = True
                                break
                            elif isinstance(data, dict):
                                items = data.get("items", data.get("data", data.get("components", data.get("indexComponents", []))))
                                if items:
                                    print(f"SUCCESS (nested)!")
                                    print(f"  URL:  {url}")
                                    print(f"  Auth: {auth_label}")
                                    print(f"  Items: {len(items)}")
                                    print(f"  Keys: {list(items[0].keys())}")
                                    print(f"  Sample:\n{json.dumps(items[0], ensure_ascii=False, indent=4)}")
                                    success_found = True
                                    break
                                else:
                                    print(f"  200 but dict with keys: {list(data.keys())} | {url} | {auth_label}")
                        except json.JSONDecodeError:
                            # 200 but not JSON - might be HTML
                            if len(content) < 200:
                                print(f"  200 non-JSON ({len(content)} chars): {content[:100]} | {url}")
                            else:
                                print(f"  200 non-JSON ({len(content)} chars, likely HTML) | {url}")
                    else:
                        pass  # 200 but empty body - skip silently
                elif response.status_code == 401:
                    # Only print 401 once per host+auth combo (not for every path)
                    pass
                elif response.status_code not in [404, 405]:
                    print(f"  {response.status_code} | {url} | {auth_label}")

            except requests.exceptions.ConnectionError:
                pass  # Host not reachable
            except Exception as e:
                print(f"  Error: {e} | {url}")

if not success_found:
    print("\nNo successful response found with any combination.")
    print("\nTrying one more thing - raw response inspection:")
    print()

    # Debug: show exactly what datahubapi returns
    for auth_name, auth_value in AUTH_FORMATS[:2]:
        headers = {
            "accept": "application/json",
            "accept-language": "he-IL",
            auth_name: auth_value,
        }
        url = "https://datahubapi.tase.co.il/api/Index/IndexComponents?indexId=142"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"  {auth_name}: {auth_value[:25]}...")
            print(f"    Status: {r.status_code}")
            print(f"    Headers: {dict(r.headers)}")
            print(f"    Body length: {len(r.text)}")
            print(f"    Body: '{r.text[:200]}'")
            print()
        except Exception as e:
            print(f"  Error: {e}")

    # Also try datawise with all auth formats
    print("Datawise.tase.co.il detailed results:")
    for auth_name, auth_value in AUTH_FORMATS:
        headers = {
            "accept": "application/json",
            "accept-language": "he-IL",
            auth_name: auth_value,
        }
        url = f"https://datawise.tase.co.il/v1/basic-indices/index-components-basic/142/{now.year}/{now.month}/{now.day}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"  {auth_name}: {auth_value[:30]}... -> {r.status_code}: {r.text[:100]}")
        except Exception as e:
            print(f"  {auth_name}: Error: {e}")