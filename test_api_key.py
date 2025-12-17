"""
Test script to verify EODHD API key loading and connection
"""
import sys
import os
import codecs

# Fix Windows console encoding for Hebrew
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env file
env_path = Path(__file__).parent / ".env"
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")

load_dotenv(override=True)

# Check if API key is loaded
api_key = os.getenv("EODHD_API_KEY")
print(f"\nEODHD_API_KEY from environment: {api_key}")
print(f"API key length: {len(api_key) if api_key else 0}")
print(f"API key is None: {api_key is None}")
print(f"API key is empty: {api_key == ''}")

if not api_key:
    print("\n❌ ERROR: EODHD_API_KEY not found in environment!")
    sys.exit(1)

# Test API connection
print(f"\n{'='*60}")
print("Testing EODHD API connection...")
print(f"{'='*60}")

url = "https://eodhd.com/api/fundamentals/AAPL.US"
params = {"api_token": api_key, "fmt": "json"}

print(f"\nRequest URL: {url}")
print(f"Request params: api_token={api_key[:10]}..., fmt=json")

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"\nResponse status code: {response.status_code}")

    if response.status_code == 200:
        print("✅ SUCCESS: API connection working!")
        data = response.json()
        print(f"Response keys: {list(data.keys())[:5]}...")
    elif response.status_code == 401:
        print("❌ ERROR: Invalid API key (401 Unauthorized)")
    elif response.status_code == 403:
        print("❌ ERROR: Access forbidden (403)")
    else:
        print(f"❌ ERROR: Unexpected status code")
        print(f"Response text: {response.text[:200]}")

except Exception as e:
    print(f"❌ ERROR: Exception occurred: {e}")

print(f"\n{'='*60}")
print("Now testing via config.settings...")
print(f"{'='*60}")

from config import settings

print(f"\nsettings.EODHD_API_KEY: {settings.EODHD_API_KEY}")
print(f"Keys match: {settings.EODHD_API_KEY == api_key}")
