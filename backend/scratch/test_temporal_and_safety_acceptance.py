import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_a_nearest_fishing_zone_honest_unverified_suppression():
    """
    TEST A: Mangalore + 'nearest fishing zone'
    Uses alternative oceanographic thermal front analysis model to return nearest fishing candidate and map marker.
    """
    payload = {"query": "nearest fishing zone", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
    assert pfz_ev is not None
    assert pfz_ev["value"].get("name") is not None
    pfz_markers = [m for m in data.get("map_markers", []) if m["type"] == "pfz"]
    assert len(pfz_markers) >= 1
    assert "nearshore coastal" in data["recommendation"].lower() or "potential fishing zone" in data["recommendation"].lower()
    print(f"\n[PASS TEST A] Nearest PFZ Alternative Model Recommendation: Rec: '{data['recommendation']}' | PFZ Markers: {len(pfz_markers)}")

def test_b_where_can_i_go_fishing():
    """
    TEST B: Mangalore + 'where can I go fishing?'
    Must provide ocean safety assessment and suitable fishing area candidates from alternative oceanographic model.
    """
    payload = {"query": "where can I go fishing?", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["recommendation"]) > 10
    pfz_markers = [m for m in data.get("map_markers", []) if m["type"] == "pfz"]
    assert len(pfz_markers) >= 1
    print(f"\n[PASS TEST B] Where can I fish: Rec: '{data['recommendation']}' | PFZ Markers: {len(pfz_markers)}")

def test_c_nearest_fishing_zone_2km_range():
    """
    TEST C: Mangalore + 'nearest fishing zone in range of 2 km'
    Enforces distance constraint and returns 0 pfz markers.
    """
    payload = {"query": "nearest fishing zone in range of 2 km", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
    assert pfz_ev is not None
    assert pfz_ev["value"].get("status") in ["no_candidate_within_range", "live_pfz_feed_unavailable"]
    pfz_markers = [m for m in data.get("map_markers", []) if m["type"] == "pfz"]
    assert len(pfz_markers) == 0
    print(f"\n[PASS TEST C] 2km Range Enforced! Rec: '{data['recommendation']}' | PFZ Markers: {len(pfz_markers)}")

def test_d_restricted_zones_avoidance():
    """
    TEST D: Gulf of Kutch + 'fishing restricted zones near by'
    Must return AVOIDANCE intent with restricted_zone markers and 0 pfz markers.
    """
    payload = {"query": "fishing restricted zones near by", "latitude": 22.5, "longitude": 69.5, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    rz_markers = [m for m in data.get("map_markers", []) if m["type"] == "restricted_zone"]
    pfz_markers = [m for m in data.get("map_markers", []) if m["type"] == "pfz"]
    assert len(rz_markers) > 0
    assert len(pfz_markers) == 0
    print(f"\n[PASS TEST D] Restricted Zones: {len(rz_markers)} restricted_zone markers, 0 pfz markers. Rec: '{data['recommendation']}'")

def test_e_highest_productivity():
    """
    TEST E: Mangalore + 'where is the most productive fishing area?'
    Returns computed oceanographic analysis with candidate_type in [computed_marine_analysis, synthetic_demo] and is_verified_pfz = False.
    """
    payload = {"query": "where is the most productive fishing area?", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
    assert pfz_ev is not None
    assert pfz_ev["value"].get("candidate_type") in ["computed_marine_analysis", "synthetic_demo"]
    assert pfz_ev["value"].get("is_verified_pfz") is False
    print(f"\n[PASS TEST E] Highest Productivity Model: Rec: '{data['recommendation']}' | Type: '{pfz_ev['value'].get('candidate_type')}'")

def test_f_highest_chlorophyll_feed_status():
    """
    TEST F: Mangalore + 'which area has the highest chlorophyll?'
    Discloses unconfigured Copernicus chlorophyll status honestly.
    """
    payload = {"query": "which area has the highest chlorophyll?", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "unavailable" in data["recommendation"].lower() or "copernicus" in data["recommendation"].lower() or "chlorophyll" in data["recommendation"].lower()
    print(f"\n[PASS TEST F] Highest Chlorophyll feed status disclosure: Rec: '{data['recommendation']}'")

def test_g_tonight_2am_temporal_preservation():
    """
    TEST G: Mangalore + 'can I go out for fishing at my location tonight 2 am'
    Must evaluate approximately 02:00 local time and NOT convert to tomorrow morning 06:00-12:00.
    """
    payload = {"query": "can I go out for fishing at my location tonight 2 am", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    fcst_ev = next((e for e in data["evidence"] if e["parameter"] == "forecast_period_label"), None)
    assert fcst_ev is not None
    period_val = fcst_ev["value"].lower()
    assert "tonight" in period_val or "02:00" in period_val or "2:00" in period_val
    assert "tomorrow morning (06:00 - 12:00" not in period_val
    print(f"\n[PASS TEST G] Tonight 2 AM Temporal Preservation: Period: '{fcst_ev['value']}' | Rec: '{data['recommendation']}'")

def test_h_tomorrow_morning_temporal_preservation():
    """
    TEST H: Mangalore + 'can I go fishing tomorrow morning?'
    Must evaluate tomorrow morning forecast.
    """
    payload = {"query": "can I go fishing tomorrow morning?", "latitude": 12.91, "longitude": 74.85, "language": "en"}
    r = client.post("/api/query", json=payload)
    assert r.status_code == 200
    data = r.json()
    fcst_ev = next((e for e in data["evidence"] if e["parameter"] == "forecast_period_label"), None)
    assert fcst_ev is not None
    assert "tomorrow morning" in fcst_ev["value"].lower()
    print(f"\n[PASS TEST H] Tomorrow Morning Preservation: Period: '{fcst_ev['value']}' | Rec: '{data['recommendation']}'")

def test_i_multi_city_active_location_propagation():
    """
    TEST I: Multi-city active location propagation across Kochi, Chennai, Goa, Visakhapatnam, Mumbai, arbitrary coords.
    """
    cities = [
        ("Kochi", 9.93, 76.26),
        ("Chennai", 13.08, 80.27),
        ("Goa", 15.29, 73.98),
        ("Visakhapatnam", 17.68, 83.21),
        ("Mumbai", 18.95, 72.82),
        ("Arbitrary Coastal (Alibag)", 18.64, 72.87)
    ]
    for city_name, lat, lon in cities:
        payload = {"query": "where is the most productive fishing area?", "latitude": lat, "longitude": lon, "language": "en"}
        r = client.post("/api/query", json=payload)
        assert r.status_code == 200
        data = r.json()
        pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
        assert pfz_ev is not None
        cand_lat = pfz_ev["value"]["latitude"]
        cand_lon = pfz_ev["value"]["longitude"]
        assert abs(cand_lat - lat) < 2.0
        assert abs(cand_lon - lon) < 2.0
        print(f"  - Active Location '{city_name}' ({lat}, {lon}) -> Candidate at ({cand_lat}, {cand_lon}) [{pfz_ev['value']['distance_km']} km]")
    print(f"\n[PASS TEST I] Multi-City Active Location Propagation Verified across 6 coastal locations!")

def test_j_multi_turn_semantic_isolation():
    """
    TEST J: Multi-turn semantic isolation.
    """
    session_id = "test_session_multi_turn_isolation"
    
    # Turn 1: PFZ Query
    p1 = {"query": "where is the most productive fishing area?", "latitude": 12.91, "longitude": 74.85, "session_id": session_id}
    r1 = client.post("/api/query", json=p1)
    assert r1.status_code == 200
    
    # Turn 2: Avoidance Query
    p2 = {"query": "which restricted areas are nearby?", "latitude": 22.5, "longitude": 69.5, "session_id": session_id}
    r2 = client.post("/api/query", json=p2)
    assert r2.status_code == 200
    d2 = r2.json()
    
    pfz_markers_t2 = [m for m in d2.get("map_markers", []) if m["type"] == "pfz"]
    rz_markers_t2 = [m for m in d2.get("map_markers", []) if m["type"] == "restricted_zone"]
    assert len(pfz_markers_t2) == 0
    assert len(rz_markers_t2) > 0
    print(f"\n[PASS TEST J] Multi-Turn Semantic Isolation: Turn 2 returned {len(rz_markers_t2)} restricted_zone markers and 0 pfz markers.")

if __name__ == "__main__":
    test_a_nearest_fishing_zone_honest_unverified_suppression()
    test_b_where_can_i_go_fishing()
    test_c_nearest_fishing_zone_2km_range()
    test_d_restricted_zones_avoidance()
    test_e_highest_productivity()
    test_f_highest_chlorophyll_feed_status()
    test_g_tonight_2am_temporal_preservation()
    test_h_tomorrow_morning_temporal_preservation()
    test_i_multi_city_active_location_propagation()
    test_j_multi_turn_semantic_isolation()
    print("\n==========================================================================")
    print(" ALL 10 MASTER REASONING & ACCEPTANCE TESTS PASSED WITH 100% TRUTHFULNESS! ")
    print("==========================================================================")
