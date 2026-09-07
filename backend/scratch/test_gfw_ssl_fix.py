import sys
sys.path.insert(0, ".")
import os
import ssl
import httpx
import json
from app.core.config import settings

def test_gfw_ssl():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API WITH CUSTOM SSL CONTEXT ===")

    # Create custom SSL Context for Windows Python 3.14
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_ciphers('DEFAULT@SECLEVEL=1')

    headers = {
        "Authorization": f"Bearer {gfw_key}",
        "User-Agent": "ORCA-Marine-Intelligence/1.0"
    }

    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    print("Requesting GFW Endpoint:", url)

    try:
        transport = httpx.HTTPTransport(verify=ctx)
        with httpx.Client(transport=transport, timeout=10.0) as client:
            r = client.get(url, headers=headers)
            print("Status Code:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                print("[SUCCESS] GFW Real API Authentication Succeeded!")
                print("Total Entries:", data.get("total", len(data.get("entries", []))))
                entries = data.get("entries", [])
                print(f"Retrieved {len(entries)} real GFW vessel activity entries.")
                if entries:
                    vessel = entries[0]
                    print("Sample GFW Vessel Record:", json.dumps({
                        "id": vessel.get("id"),
                        "shipname": vessel.get("shipname"),
                        "flag": vessel.get("flag"),
                        "ssvid": vessel.get("ssvid"),
                        "firstTransmissionDate": vessel.get("firstTransmissionDate"),
                        "lastTransmissionDate": vessel.get("lastTransmissionDate")
                    }, indent=2))
            else:
                print("Error Response Body:", r.text[:300])
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    test_gfw_ssl()
