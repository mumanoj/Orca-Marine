import sys
sys.path.insert(0, ".")
import httpx
import json

def test_erddap_correct_dims():
    lat = 12.91
    lon = 74.85
    min_lat = round(lat - 0.5, 2)
    max_lat = round(lat + 0.5, 2)
    min_lon = round(lon - 0.5, 2)
    max_lon = round(lon + 0.5, 2)

    headers = {"User-Agent": "ORCA-Marine-Platform/1.0"}

    # 1. High-Res MUR SST (3 dimensions: time, latitude, longitude)
    mur_sst_url = f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.json?analysed_sst[(last)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"
    
    # 2. NOAA CoastWatch Blended SST (3 dimensions: time, latitude, longitude)
    blended_sst_url = f"https://coastwatch.noaa.gov/erddap/griddap/noaacwBLENDEDsstDaily.json?sst[(last)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"

    # 3. VIIRS Chlorophyll 8-Day Composite (3 dimensions: time, latitude, longitude)
    chla_8day_url = f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdVH2018chla8day.json?chla[(last)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"

    print("=== TESTING CORRECT DIMENSION SATELLITE REQUESTS ===")

    print("\n--- 1. JPL MUR SST (jplMURSST41) ---")
    print("URL:", mur_sst_url)
    try:
        r = httpx.get(mur_sst_url, headers=headers, follow_redirects=True, timeout=10.0)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            table = data.get("table", {})
            rows = table.get("rows", [])
            valid_rows = [row for row in rows if row[-1] is not None]
            print(f"Retrieved {len(rows)} data points. Valid Non-Null SST Points: {len(valid_rows)}")
            if valid_rows:
                sst_k = valid_rows[0][-1]
                sst_c = round(sst_k - 273.15, 2) if sst_k > 200 else sst_k
                print(f"SAMPLE SST: {sst_c} °C | Time: {valid_rows[0][0]}")
        else:
            print("Response:", r.text[:200])
    except Exception as e:
        print("Error:", e)

    print("\n--- 2. NOAA Blended SST (noaacwBLENDEDsstDaily) ---")
    print("URL:", blended_sst_url)
    try:
        r = httpx.get(blended_sst_url, headers=headers, follow_redirects=True, timeout=10.0)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            table = data.get("table", {})
            rows = table.get("rows", [])
            valid_rows = [row for row in rows if row[-1] is not None]
            print(f"Retrieved {len(rows)} data points. Valid Non-Null SST Points: {len(valid_rows)}")
            if valid_rows:
                print(f"SAMPLE SST: {valid_rows[0][-1]} °C | Time: {valid_rows[0][0]}")
        else:
            print("Response:", r.text[:200])
    except Exception as e:
        print("Error:", e)

    print("\n--- 3. VIIRS Chlorophyll 8-Day (erdVH2018chla8day) ---")
    print("URL:", chla_8day_url)
    try:
        r = httpx.get(chla_8day_url, headers=headers, follow_redirects=True, timeout=10.0)
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            table = data.get("table", {})
            rows = table.get("rows", [])
            valid_rows = [row for row in rows if row[-1] is not None]
            print(f"Retrieved {len(rows)} data points. Valid Non-Null Chlorophyll Points: {len(valid_rows)}")
            if valid_rows:
                print(f"SAMPLE Chlorophyll-a: {valid_rows[0][-1]} mg/m³ | Time: {valid_rows[0][0]}")
        else:
            print("Response:", r.text[:200])
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_erddap_correct_dims()
