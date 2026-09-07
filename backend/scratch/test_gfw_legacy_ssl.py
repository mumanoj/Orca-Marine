import sys
sys.path.insert(0, ".")
import os
import ssl
import httpx
import json
from app.core.config import settings

def test_gfw_legacy_ssl():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API WITH LEGACY SSL OPTIONS ===")

    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.options |= getattr(ssl, 'OP_LEGACY_SERVER_CONNECT', 0x4)
    except Exception as e:
        print("Legacy option set error:", e)

    headers = {
        "Authorization": f"Bearer {gfw_key}",
        "User-Agent": "ORCA-Marine-Intelligence/1.0",
        "Accept": "application/json"
    }

    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    print("Requesting:", url)

    try:
        transport = httpx.HTTPTransport(verify=ctx)
        with httpx.Client(transport=transport, timeout=15.0) as client:
            r = client.get(url, headers=headers)
            print("Status Code:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                print("[SUCCESS] Real GFW API Authentication & Response Successful!")
                print("Total Entries Found:", data.get("total", len(data.get("entries", []))))
                entries = data.get("entries", [])
                print(f"Retrieved {len(entries)} real GFW vessel records.")
                if entries:
                    print("Sample Vessel:", entries[0])
            else:
                print("Error Response Body:", r.text[:300])
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    test_gfw_legacy_ssl()
