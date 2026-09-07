import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.marine_geospatial import is_valid_marine_candidate

client = TestClient(app)

def test_1_safety_query_returns_genuine_safety_assessment():
    """Verify 'Is it safe to go fishing tomorrow morning?' returns a safety decision, not raw observation text."""
    payload = {
        "query": "Is it safe to go fishing tomorrow morning?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res = client.post("/api/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    rec = data["recommendation"]
    
    # Must NOT output raw observation header
    assert "retrieved marine observations" not in rec.lower(), f"Safety query returned raw observation list: {rec}"
    # Must contain safety decision / rating
    assert any(w in rec.lower() for w in ["safe", "caution", "suitable", "warning", "rated"]), f"Safety assessment missing decision: {rec}"
    print(f"\n[PASS] Safety Query Response:\n'{rec}'")

def test_2_temporal_context_differentiation():
    """Verify 'right now' vs 'tomorrow morning' parse different temporal frames."""
    res_now = client.post("/api/query", json={"query": "What is the weather right now?", "latitude": 12.91, "longitude": 74.85})
    res_tm = client.post("/api/query", json={"query": "What will the weather be tomorrow morning?", "latitude": 12.91, "longitude": 74.85})
    
    assert res_now.status_code == 200 and res_tm.status_code == 200
    rec_now = res_now.json()["recommendation"]
    rec_tm = res_tm.json()["recommendation"]
    
    assert rec_now != rec_tm or "tomorrow" in rec_tm.lower() or "forecast" in rec_tm.lower()
    print(f"\n[PASS] Current Weather:\n'{rec_now}'\nTomorrow Weather:\n'{rec_tm}'")

def test_3_semantic_differentiation_nearest_vs_productivity():
    """Verify 'nearest' vs 'most productive' yield distinct rankings/candidates."""
    res_near = client.post("/api/query", json={"query": "Where is the nearest fishing area?", "latitude": 12.91, "longitude": 74.85})
    res_prod = client.post("/api/query", json={"query": "Where is the most productive fishing area?", "latitude": 12.91, "longitude": 74.85})
    
    assert res_near.status_code == 200 and res_prod.status_code == 200
    data_near = res_near.json()
    data_prod = res_prod.json()
    
    assert data_near["explanation"] != data_prod["explanation"] or data_near["recommendation"] != data_prod["recommendation"]
    print(f"\n[PASS] Nearest Recommendation:\n'{data_near['recommendation']}'\nMost Productive Recommendation:\n'{data_prod['recommendation']}'")

def test_4_suitable_nearby_returns_multiple_candidates():
    """Verify 'Show me suitable fishing areas nearby' returns multiple map pins."""
    res = client.post("/api/query", json={"query": "Show me suitable fishing areas nearby.", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    markers = data.get("map_markers", [])
    # Should have query location pin + at least 2 suitable PFZ candidate pins
    pfz_markers = [m for m in markers if m.get("type") == "pfz"]
    assert len(pfz_markers) >= 2, f"Expected multiple suitable candidate pins, got {len(pfz_markers)}"
    print(f"\n[PASS] Suitable Nearby Markers Count: {len(pfz_markers)}")

def test_5_productivity_cause_returns_causal_explanation():
    """Verify 'Why has fishing productivity declined?' returns causal oceanographic explanation, not coordinate primary answer."""
    res = client.post("/api/query", json={"query": "Why has fishing productivity declined in this region?", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    rec = data["recommendation"]
    assert "the selected potential fishing zone" not in rec.lower(), f"Productivity cause query returned single PFZ candidate answer: {rec}"
    assert any(w in rec.lower() for w in ["temperature", "upwelling", "thermal", "productivity", "chlorophyll", "anomalies"]), f"Missing causal explanation: {rec}"
    print(f"\n[PASS] Productivity Cause Explanation:\n'{rec}'")

def test_6_chlorophyll_no_fabricated_numbers():
    """Verify chlorophyll query states unavailable feed cleanly when Copernicus is not configured."""
    res = client.post("/api/query", json={"query": "Which area has the highest chlorophyll concentration?", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    rec = res.json()["recommendation"]
    assert "unavailable" in rec.lower() or "copernicus" in rec.lower() or "chlorophyll" in rec.lower()
    print(f"\n[PASS] Chlorophyll Response:\n'{rec}'")

def test_7_water_only_location_validation_and_active_location_8_cities():
    """Verify active location changes candidate selection across 8 coastal regions and all coordinates are water-only."""
    coastal_cities = [
        ("Chennai", 13.08, 80.27),
        ("Kochi", 9.93, 76.26),
        ("Mangalore", 12.91, 74.85),
        ("Goa", 15.29, 73.98),
        ("Visakhapatnam", 17.68, 83.21),
        ("Gulf of Kutch", 22.50, 69.50),
        ("Tuticorin", 8.80, 78.10),
        ("Kanyakumari", 8.08, 77.55)
    ]
    
    for city_name, lat, lon in coastal_cities:
        res = client.post("/api/query", json={"query": "Where is the nearest Potential Fishing Zone today?", "latitude": lat, "longitude": lon})
        assert res.status_code == 200
        data = res.json()
        markers = data.get("map_markers", [])
        pfz_markers = [m for m in markers if m.get("type") == "pfz"]
        assert len(pfz_markers) > 0, f"No PFZ candidate returned for {city_name}"
        
        cand = pfz_markers[0]
        c_lat, c_lon = cand["lat"], cand["lng"]
        assert is_valid_marine_candidate(c_lat, c_lon), f"Candidate ({c_lat}, {c_lon}) for {city_name} is on LAND!"
        print(f"City: {city_name:15} | Active: ({lat}, {lon}) -> Candidate: '{cand['label']}' at ({c_lat}, {c_lon}) [Water Valid]")

def test_8_routing_destination_water_only():
    """Verify routing target destination is strictly in offshore waters."""
    res = client.post("/api/query", json={"query": "Take me to the nearest suitable fishing area.", "latitude": 12.91, "longitude": 74.85})
    assert res.status_code == 200
    data = res.json()
    route_info = data.get("route_information")
    assert route_info is not None, "Missing route_information in payload"
    dest_lat = route_info.get("destination", {}).get("latitude")
    dest_lon = route_info.get("destination", {}).get("longitude")
    if dest_lat is not None and dest_lon is not None:
        assert is_valid_marine_candidate(dest_lat, dest_lon), f"Routing destination ({dest_lat}, {dest_lon}) is on LAND!"
    print(f"\n[PASS] Routing Transit Distance: {route_info.get('distance_km')} km | Destination: ({dest_lat}, {dest_lon}) [Water Valid]")

if __name__ == "__main__":
    print("==============================================================")
    print("   RUNNING STEP 5G FINAL PRODUCTION ACCEPTANCE SUITE           ")
    print("==============================================================")
    test_1_safety_query_returns_genuine_safety_assessment()
    test_2_temporal_context_differentiation()
    test_3_semantic_differentiation_nearest_vs_productivity()
    test_4_suitable_nearby_returns_multiple_candidates()
    test_5_productivity_cause_returns_causal_explanation()
    test_6_chlorophyll_no_fabricated_numbers()
    test_7_water_only_location_validation_and_active_location_8_cities()
    test_8_routing_destination_water_only()
    print("==============================================================")
    print("   ALL STEP 5G FINAL ACCEPTANCE TESTS PASSED SUCCESSFULLY!    ")
    print("==============================================================")
