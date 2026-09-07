import sys
sys.path.insert(0, ".")
import httpx
import json

def test_erddap():
    lat = 12.91
    lon = 74.85
    min_lat = round(lat - 0.2, 3)
    max_lat = round(lat + 0.2, 3)
    min_lon = round(lon - 0.2, 3)
    max_lon = round(lon + 0.2, 3)

    # Correct ERDDAP Endpoint & Dataset ID
    # 1. Chlorophyll-a: noaacwN20VIIRSchlaDaily
    chla_url = f"https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaDaily.json?chlor_a[(last)][(0.0)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"
    
    # 2. SST: noaacwBLENDEDsstDaily
    sst_url = f"https://coastwatch.noaa.gov/erddap/griddap/noaacwBLENDEDsstDaily.json?sst[(last)][(0.0)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"

    headers = {"User-Agent": "ORCA-Marine-Platform/1.0"}

    print("=== STEP 3: TESTING CORRECTED DIRECT ERDDAP REQUESTS ===")
    print("\n--- 1. Chlorophyll Request ---")
    print("URL:", chla_url)
    try:
        r = httpx.get(chla_url, headers=headers, follow_redirects=True, timeout=8.0)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            table = data.get("table", {})
            column_names = table.get("columnNames", [])
            rows = table.get("rows", [])
            print("Columns:", column_names)
            print(f"Retrieved {len(rows)} data points.")
            valid_rows = [row for row in rows if row[-1] is not None]
            print(f"Valid Non-Null Chlorophyll Points: {len(valid_rows)}")
            if valid_rows:
                print("Sample Valid Data Point:", valid_rows[0])
        else:
            print("Error Response:", r.text[:300])
    except Exception as e:
        print("Chlorophyll Exception:", e)

    print("\n--- 2. SST Request ---")
    print("URL:", sst_url)
    try:
        r = httpx.get(sst_url, headers=headers, follow_redirects=True, timeout=8.0)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            table = data.get("table", {})
            column_names = table.get("columnNames", [])
            rows = table.get("rows", [])
            print("Columns:", column_names)
            print(f"Retrieved {len(rows)} data points.")
            valid_rows = [row for row in rows if row[-1] is not None]
            print(f"Valid Non-Null SST Points: {len(valid_rows)}")
            if valid_rows:
                print("Sample Valid Data Point:", valid_rows[0])
        else:
            print("Error Response:", r.text[:300])
    except Exception as e:
        print("SST Exception:", e)

if __name__ == "__main__":
    test_erddap()
