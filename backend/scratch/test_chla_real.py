import sys
sys.path.insert(0, ".")
import httpx
import json

def test_chla_real():
    lat = 12.91
    lon = 74.85
    min_lat = round(lat - 0.5, 2)
    max_lat = round(lat + 0.5, 2)
    min_lon = round(lon - 0.5, 2)
    max_lon = round(lon + 0.5, 2)

    headers = {"User-Agent": "ORCA-Marine-Platform/1.0"}

    # Chlorophyll Datasets to Test
    chla_queries = [
        # MODIS Monthly (always has 100% cloud-free composite data)
        ("erdMH1chlamday", "chlorophyll", f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdMH1chlamday.json?chlorophyll[(last)][(12.41):1:(13.41)][(74.35):1:(75.35)]"),
        # VIIRS 8-Day NOAA CoastWatch
        ("noaacwN20VIIRSchla8Day", "chlor_a", f"https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchla8Day.json?chlor_a[(last)][(0.0)][(12.41):1:(13.41)][(74.35):1:(75.35)]"),
        # VIIRS 8-Day Time Offset [(last-3)]
        ("erdVH2018chla8day", "chla", f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdVH2018chla8day.json?chla[(last-3)][(12.41):1:(13.41)][(74.35):1:(75.35)]")
    ]

    print("=== TESTING CHLOROPHYLL-A REAL SATELLITE RETRIEVAL ===")
    for name, var_name, url in chla_queries:
        print(f"\n--- Testing {name} ---")
        print("URL:", url)
        try:
            r = httpx.get(url, headers=headers, follow_redirects=True, timeout=10.0)
            print("Status Code:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                table = data.get("table", {})
                rows = table.get("rows", [])
                valid_rows = [row for row in rows if row[-1] is not None]
                print(f"Retrieved {len(rows)} data points. Valid Non-Null Chlorophyll Points: {len(valid_rows)}")
                if valid_rows:
                    chla_val = round(valid_rows[0][-1], 3)
                    time_val = valid_rows[0][0]
                    print(f"[SUCCESS] Real Chlorophyll-a: {chla_val} mg/m³ | Time: {time_val}")
            else:
                print("Error Response:", r.text[:200])
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    test_chla_real()
