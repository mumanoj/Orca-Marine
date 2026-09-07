import sys
sys.path.insert(0, ".")
import os
import subprocess
import json
from app.core.config import settings

def test_gfw_curl_subprocess():
    gfw_key = settings.GFW_API_KEY or os.getenv("GFW_API_KEY")
    print("=== TESTING GFW REAL API VIA SUBPROCESS CURL (--ssl-no-revoke) ===")
    
    url = "https://gateway.globalfishingwatch.org/v3/vessels/search?query=india&limit=5"
    auth_header = f"Authorization: Bearer {gfw_key}"

    cmd = ["curl.exe", "--ssl-no-revoke", "-s", "-k", "-H", auth_header, "-H", "Accept: application/json", url]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print("Return Code:", res.returncode)
        if res.returncode == 0 and res.stdout:
            try:
                data = json.loads(res.stdout)
                print("[SUCCESS] Real GFW API Authentication & Response Succeeded!")
                print("Total Entries Found:", data.get("total", len(data.get("entries", []))))
                entries = data.get("entries", [])
                print(f"Retrieved {len(entries)} real GFW vessel records.")
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
            except Exception as pe:
                print("Raw Response Output (first 300 chars):", res.stdout[:300])
        else:
            print("Stderr Output:", res.stderr[:300])
            print("Stdout Output:", res.stdout[:300])
    except Exception as e:
        print("Subprocess Exception:", e)

if __name__ == "__main__":
    test_gfw_curl_subprocess()
