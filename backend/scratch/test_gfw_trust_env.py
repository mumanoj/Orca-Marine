import sys
sys.path.insert(0, ".")
import os
import httpx
import json
from app.core.config import settings

def test_gfw_trust_env():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API WITH TRUST_ENV=FALSE & TIMEOUT ===")
    
    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    headers = {
        "Authorization": f"Bearer {gfw_key}",
        "User-Agent": "ORCA-Marine-Platform/1.0"
    }

    try:
        with httpx.Client(trust_env=False, verify=False, timeout=10.0) as client:
            r = client.get(url, headers=headers)
            print("Status Code:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                print("[SUCCESS] GFW API Authentication & Retrieval Successful!")
                print("Response Data:", str(data)[:300])
            else:
                print("Response Body:", r.text[:300])
    except Exception as e:
        print("Exception:", type(e).__name__, ":", e)

if __name__ == "__main__":
    test_gfw_trust_env()
