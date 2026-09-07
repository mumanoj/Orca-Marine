import sys
sys.path.insert(0, ".")
import os
import httpx
import json
from app.core.config import settings

def test_gfw_live():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API AUTHENTICATION & ENDPOINTS ===")
    print(f"GFW API Key Present: {bool(gfw_key)}")
    if not gfw_key:
        print("ERROR: GFW_API_KEY is missing from environment.")
        return

    headers = {
        "Authorization": f"Bearer {gfw_key}",
        "User-Agent": "ORCA-Marine-Intelligence/1.0",
        "Accept": "application/json"
    }

    # Test Endpoints
    endpoints = [
        ("Vessels Search (India)", "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"),
        ("Vessels Self Info", "https://gateway.globalfishingwatch.org/v3/vessels"),
        ("Datasets List", "https://gateway.globalfishingwatch.org/v3/datasets")
    ]

    for name, url in endpoints:
        print(f"\n--- Testing {name} ---")
        print("URL:", url)
        try:
            r = httpx.get(url, headers=headers, verify=False, timeout=10.0)
            print("Status Code:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                print(f"[SUCCESS] Auth OK! Retrieved {len(data.get('entries', [])) if isinstance(data, dict) else len(data)} items.")
                print("Sample Data:", str(data)[:300])
            else:
                print("Response Body:", r.text[:300])
        except Exception as e:
            print("Exception:", e)

if __name__ == "__main__":
    test_gfw_live()
