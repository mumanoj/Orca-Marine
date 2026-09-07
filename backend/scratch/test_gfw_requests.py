import sys
sys.path.insert(0, ".")
import os
import requests
import json
from app.core.config import settings

def test_gfw_requests():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API WITH REQUESTS / CURL ===")
    
    headers = {
        "Authorization": f"Bearer {gfw_key}",
        "User-Agent": "ORCA-Marine-Intelligence/1.0",
        "Accept": "application/json"
    }

    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    print("URL:", url)

    try:
        r = requests.get(url, headers=headers, timeout=10.0, verify=False)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            print("[SUCCESS] GFW API Authentication & Response Successful!")
            print("Total Entries Found:", data.get("total", len(data.get("entries", []))))
            if "entries" in data and data["entries"]:
                sample_vessel = data["entries"][0]
                print(f"Sample Vessel ID: {sample_vessel.get('id')}")
                print(f"Sample Vessel Name: {sample_vessel.get('shipname') or sample_vessel.get('flag')}")
            print("Sample Json:", str(data)[:300])
        else:
            print("Response:", r.text[:300])
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    test_gfw_requests()
