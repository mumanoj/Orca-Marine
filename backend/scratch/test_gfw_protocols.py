import sys
sys.path.insert(0, ".")
import os
import ssl
import urllib.request
import json
from app.core.config import settings

def test_gfw_urllib():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API WITH URLLIB & TLS 1.2 ===")

    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {gfw_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10.0) as resp:
            status = resp.status
            body = resp.read().decode('utf-8')
            print("Status Code:", status)
            if status == 200:
                data = json.loads(body)
                print("[SUCCESS] Real GFW API Auth & Data Retrieval Successful!")
                print("Total Entries:", data.get("total", len(data.get("entries", []))))
                entries = data.get("entries", [])
                print(f"Retrieved {len(entries)} real GFW vessel activity entries.")
                if entries:
                    print("Sample GFW Vessel:", entries[0].get("shipname"), "| ID:", entries[0].get("id"))
            else:
                print("Body:", body[:300])
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    test_gfw_urllib()
