import sys
sys.path.insert(0, ".")
import os
import socket
import ssl
import httpx
import json
from app.core.config import settings

def test_gfw_sni():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API WITH EXPLICIT SNI & OP_NO_TICKET ===")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= getattr(ssl, 'OP_NO_TICKET', 0)

    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    headers = {
        "Authorization": f"Bearer {gfw_key}",
        "User-Agent": "ORCA-Marine-Platform/1.0",
        "Host": "gateway.globalfishingwatch.org"
    }

    try:
        transport = httpx.HTTPTransport(verify=ctx)
        with httpx.Client(transport=transport, timeout=10.0) as client:
            r = client.get(url, headers=headers)
            print("Status Code:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                print("[SUCCESS] Real GFW API Authentication Succeeded!")
                print("Total Found:", data.get("total"))
                print("Entries:", str(data.get("entries"))[:300])
            else:
                print("Response:", r.text[:300])
    except Exception as e:
        print("Exception:", type(e).__name__, ":", e)

if __name__ == "__main__":
    test_gfw_sni()
