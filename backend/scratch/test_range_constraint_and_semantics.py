import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_query_1_nearest_fishing_zone_unconstrained():
    """
    Query 1: 'nearest fishing zone' at Mangalore (12.91, 74.85)
    Should return nearest valid offshore candidate (approx 38.2 km).
    """
    payload = {
        "query": "nearest fishing zone",
        "mode": "B",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
    assert pfz_ev is not None
    assert pfz_ev["value"]["distance_km"] > 0
    assert pfz_ev["value"].get("status") != "no_candidate_within_range"
    print(f"\n[PASS Query 1] Nearest PFZ: '{pfz_ev['value']['name']}' ({pfz_ev['value']['distance_km']} km)")

def test_query_2_nearest_fishing_zone_2km_range():
    """
    Query 2: 'nearest fishing zone in range of 2 km' at Mangalore (12.91, 74.85)
    MUST extract max_distance_km=2.0 and report NO candidate within 2 km instead of returning 38.2 km!
    """
    payload = {
        "query": "nearest fishing zone in range of 2 km",
        "mode": "B",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
    assert pfz_ev is not None
    assert pfz_ev["value"].get("status") == "no_candidate_within_range"
    assert pfz_ev["value"]["requested_max_distance_km"] == 2.0
    assert pfz_ev["value"]["nearest_available_distance_km"] > 30.0
    
    # Verify recommendation states clearly no zone within 2 km
    rec = data["recommendation"].lower()
    assert "no" in rec or "unavailable" in rec or "within 2" in rec or "2 km" in rec
    assert "38" in rec or "nearest available" in rec or "offshore" in rec
    
    # Map markers must NOT have a pfz marker
    pfz_markers = [m for m in data.get("map_markers", []) if m["type"] == "pfz"]
    assert len(pfz_markers) == 0
    print(f"\n[PASS Query 2] 2km Range Enforced! Rec: '{data['recommendation']}' | PFZ Markers: {len(pfz_markers)}")

def test_query_3_fishing_zones_within_2km():
    """
    Query 3: 'fishing zones within 2 km' at Mangalore (12.91, 74.85)
    MUST extract max_distance_km=2.0 and enforce constraint.
    """
    payload = {
        "query": "fishing zones within 2 km",
        "mode": "B",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
    assert pfz_ev is not None
    assert pfz_ev["value"].get("status") == "no_candidate_within_range"
    assert pfz_ev["value"]["requested_max_distance_km"] == 2.0
    print(f"\n[PASS Query 3] Within 2km Enforced! Rec: '{data['recommendation']}'")

def test_query_4_where_can_i_go_fishing():
    """
    Query 4: 'where can I go fishing?' at Mangalore (12.91, 74.85)
    Must produce contextually appropriate local candidate.
    """
    payload = {
        "query": "where can I go fishing?",
        "mode": "B",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone" or e["parameter"] == "ranked_pfz_candidates"), None)
    assert pfz_ev is not None
    print(f"\n[PASS Query 4] General Fishing Request: Rec: '{data['recommendation']}'")

def test_query_5_fishing_restricted_zones_nearby():
    """
    Query 5: 'fishing restricted zones near by'
    A. At Mangalore (12.91, 74.85) -> Clear of restrictions, 0 PFZ markers.
    B. At Gulf of Kutch (22.5, 69.5) -> Returns restricted_zone markers, 0 PFZ markers.
    """
    # Test A: Mangalore (Clear area)
    payload_clear = {
        "query": "fishing restricted zones near by",
        "mode": "B",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res_clear = client.post("/api/query", json=payload_clear)
    assert res_clear.status_code == 200
    data_clear = res_clear.json()
    pfz_markers_clear = [m for m in data_clear.get("map_markers", []) if m["type"] == "pfz"]
    assert len(pfz_markers_clear) == 0
    assert "clear" in data_clear["recommendation"].lower() or "no known" in data_clear["recommendation"].lower()

    # Test B: Gulf of Kutch (Protected Area)
    payload_restr = {
        "query": "fishing restricted zones near by",
        "mode": "B",
        "latitude": 22.5,
        "longitude": 69.5,
        "language": "en"
    }
    res_restr = client.post("/api/query", json=payload_restr)
    assert res_restr.status_code == 200
    data_restr = res_restr.json()
    
    rz_markers = [m for m in data_restr.get("map_markers", []) if m["type"] == "restricted_zone"]
    pfz_markers_restr = [m for m in data_restr.get("map_markers", []) if m["type"] == "pfz"]
    
    assert len(rz_markers) > 0
    assert len(pfz_markers_restr) == 0
    print(f"\n[PASS Query 5] Restricted Zones: Mangalore clear (0 PFZ), Gulf of Kutch ({len(rz_markers)} restricted_zone markers, 0 PFZ markers). Rec: '{data_restr['recommendation']}'")

if __name__ == "__main__":
    test_query_1_nearest_fishing_zone_unconstrained()
    test_query_2_nearest_fishing_zone_2km_range()
    test_query_3_fishing_zones_within_2km()
    test_query_4_where_can_i_go_fishing()
    test_query_5_fishing_restricted_zones_nearby()
    print("\n==============================================================")
    print(" ALL 5 REGRESSION RANGE & SEMANTIC TESTS PASSED SUCCESSFULLY! ")
    print("==============================================================")
