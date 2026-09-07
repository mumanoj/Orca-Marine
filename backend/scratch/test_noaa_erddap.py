import httpx

def test_viirs_query():
    ds_id = "nesdisVHNnoaa20chlaDaily"
    # Test variable names: 'chlor_a', 'chlorophyll', 'chla'
    for var in ["chlor_a", "chlorophyll", "chla"]:
        url = f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/{ds_id}.json?{var}[(last)][(0.0)][(12.80):1:(13.00)][(74.40):1:(74.80)]"
        headers = {"User-Agent": "ORCA-Marine-Intelligence/1.0"}
        try:
            r = httpx.get(url, headers=headers, follow_redirects=True, timeout=8.0)
            print(f"Var '{var}': Status {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                rows = data.get("table", {}).get("rows", [])
                valid = [row for row in rows if len(row) > 4 and row[4] is not None]
                print(f"  SUCCESS! Rows={len(rows)}, Valid Values={len(valid)}")
                if valid:
                    print(f"  Sample Value: {valid[0][4]} mg/m3 at {valid[0][0]}")
                break
            else:
                print("  Err msg:", r.text[:200])
        except Exception as e:
            print("  Exception:", e)

if __name__ == "__main__":
    test_viirs_query()
