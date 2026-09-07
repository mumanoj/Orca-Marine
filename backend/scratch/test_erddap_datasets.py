import sys
sys.path.insert(0, ".")
import httpx
import json

def test_erddap_datasets():
    lat = 12.91
    lon = 74.85
    min_lat = round(lat - 0.5, 2)
    max_lat = round(lat + 0.5, 2)
    min_lon = round(lon - 0.5, 2)
    max_lon = round(lon + 0.5, 2)

    headers = {"User-Agent": "ORCA-Marine-Platform/1.0"}

    # Chlorophyll Datasets to Test
    chla_datasets = [
        ("noaacwN20VIIRSchlaDaily", "chlor_a", "https://coastwatch.noaa.gov/erddap/griddap/"),
        ("erdVHNchlaDaily", "chla", "https://coastwatch.pfeg.noaa.gov/erddap/griddap/"),
        ("erdVH2018chla8day", "chla", "https://coastwatch.pfeg.noaa.gov/erddap/griddap/"),
        ("erdMH1chlamday", "chlorophyll", "https://coastwatch.pfeg.noaa.gov/erddap/griddap/")
    ]

    # SST Datasets to Test
    sst_datasets = [
        ("jplMURSST41", "analysed_sst", "https://coastwatch.pfeg.noaa.gov/erddap/griddap/"),
        ("noaacwBLENDEDsstDaily", "sea_surface_temperature", "https://coastwatch.noaa.gov/erddap/griddap/"),
        ("erdN20sstDaily", "sst", "https://coastwatch.pfeg.noaa.gov/erddap/griddap/")
    ]

    print("=== TESTING ERDDAP SATELLITE DATASETS ===")

    print("\n--- Testing Chlorophyll Datasets ---")
    for ds_id, var_name, base_url in chla_datasets:
        url = f"{base_url}{ds_id}.json?{var_name}[(last)][(0.0)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"
        try:
            r = httpx.get(url, headers=headers, follow_redirects=True, timeout=8.0)
            if r.status_code == 200:
                data = r.json()
                rows = data.get("table", {}).get("rows", [])
                valid_rows = [row for row in rows if row[-1] is not None]
                time_val = rows[0][0] if rows else "N/A"
                print(f"[SUCCESS] {ds_id} ({var_name}): {len(valid_rows)}/{len(rows)} valid points | Time: {time_val}")
                if valid_rows:
                    print(f"   Sample Value: {valid_rows[0][-1]}")
            else:
                print(f"[FAIL {r.status_code}] {ds_id}: {r.text[:120]}")
        except Exception as e:
            print(f"[ERROR] {ds_id}: {e}")

    print("\n--- Testing SST Datasets ---")
    for ds_id, var_name, base_url in sst_datasets:
        url = f"{base_url}{ds_id}.json?{var_name}[(last)][(0.0)][({min_lat}):1:({max_lat})][({min_lon}):1:({max_lon})]"
        try:
            r = httpx.get(url, headers=headers, follow_redirects=True, timeout=8.0)
            if r.status_code == 200:
                data = r.json()
                rows = data.get("table", {}).get("rows", [])
                valid_rows = [row for row in rows if row[-1] is not None]
                time_val = rows[0][0] if rows else "N/A"
                print(f"[SUCCESS] {ds_id} ({var_name}): {len(valid_rows)}/{len(rows)} valid points | Time: {time_val}")
                if valid_rows:
                    val = valid_rows[0][-1]
                    # convert Kelvin if > 200
                    if isinstance(val, (int, float)) and val > 200:
                        val = round(val - 273.15, 2)
                    print(f"   Sample SST: {val} °C")
            else:
                print(f"[FAIL {r.status_code}] {ds_id}: {r.text[:120]}")
        except Exception as e:
            print(f"[ERROR] {ds_id}: {e}")

if __name__ == "__main__":
    test_erddap_datasets()
