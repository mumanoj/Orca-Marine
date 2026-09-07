import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

def test_live_api():
    print("=== TESTING LIVE RUNNING BACKEND SERVER (http://127.0.0.1:8000) ===")
    
    # 1. Test "nearest fishing zone"
    req1 = {
        "query": "nearest fishing zone",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    r1 = httpx.post(f"{BASE_URL}/api/query", json=req1, timeout=10.0)
    print(f"\n[1. LIVE API] 'nearest fishing zone'")
    print(f"Status: {r1.status_code}")
    d1 = r1.json()
    print(f"Recommendation: {d1.get('recommendation')}")
    print(f"Map Markers ({len(d1.get('map_markers', []))}): {d1.get('map_markers')}")

    # 2. Test "nearest fishing zone in range of 2 km"
    req2 = {
        "query": "nearest fishing zone in range of 2 km",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    r2 = httpx.post(f"{BASE_URL}/api/query", json=req2, timeout=10.0)
    print(f"\n[2. LIVE API] 'nearest fishing zone in range of 2 km'")
    print(f"Status: {r2.status_code}")
    d2 = r2.json()
    print(f"Recommendation: {d2.get('recommendation')}")
    print(f"Map Markers ({len(d2.get('map_markers', []))}): {d2.get('map_markers')}")

    # 3. Test "fishing restricted zones near by"
    req3 = {
        "query": "fishing restricted zones near by",
        "latitude": 22.5,
        "longitude": 69.5,
        "language": "en"
    }
    r3 = httpx.post(f"{BASE_URL}/api/query", json=req3, timeout=10.0)
    print(f"\n[3. LIVE API] 'fishing restricted zones near by'")
    print(f"Status: {r3.status_code}")
    d3 = r3.json()
    print(f"Recommendation: {d3.get('recommendation')}")
    print(f"Map Markers ({len(d3.get('map_markers', []))}): {d3.get('map_markers')}")

if __name__ == "__main__":
    test_live_api()
