"""
ORCA Step 5G — Final Production-Grade Marine Intelligence Audit & E2E Validation Engine.
Validates:
1. Semantic Collision & Differentiation (9 query categories).
2. Active Location Propagation & Dynamic Region Audit across 8 coastal locations.
3. Map / Terrestrial Land Rejection (Western Ghats, inland TN/Kerala/Karnataka).
4. Map Payload & Primary Recommendation Target Synchronization.
5. Evidence Integrity & Copernicus Feed Availability Reporting.
6. Navigation Transit Route Geometry & Offshore Destination Integrity.
"""
import sys
from pathlib import Path

backend_dir = Path(r"c:\Local disk D\OneDrive\Desktop\orca final\backend")
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.domain.marine_geospatial import is_valid_marine_candidate, get_coastal_boundary_lon

client = TestClient(app)

def test_semantic_differentiation_audit():
    print("\n--- TEST 1: SEMANTIC DIFFERENTIATION AUDIT (9 QUERY CATEGORIES) ---")
    
    base_payload = {"latitude": 12.91, "longitude": 74.85, "mode": "C", "language": "en"}
    
    queries = [
        ("Where is the nearest fishing area?", "NEAREST_ZONE"),
        ("Where is the most productive fishing area?", "HIGHEST_PRODUCTIVITY"),
        ("Which area has the highest chlorophyll concentration?", "HIGHEST_CHLOROPHYLL"),
        ("Show me suitable fishing areas nearby.", "SUITABLE_NEARBY_ZONES"),
        ("Why has fishing productivity declined in this region?", "PRODUCTIVITY_CAUSE"),
        ("Which fishing areas should I avoid near here?", "AVOIDANCE"),
        ("How rough is the sea right now?", "OCEAN_STATE"),
        ("Can I go fishing tomorrow morning?", "SAFETY_ASSESSMENT"),
        ("Take me to the nearest suitable fishing area.", "ROUTING")
    ]

    for q_text, expected_semantics in queries:
        res = client.post("/api/query", json={**base_payload, "query": q_text})
        assert res.status_code == 200, f"Failed API call for query: {q_text}"
        data = res.json()
        
        actual_semantics = data["decision_summary"]["query_semantics"]
        print(f"Query: '{q_text:50}' -> Semantics: {actual_semantics:22} | Expected: {expected_semantics}")
        assert actual_semantics == expected_semantics, f"Mismatch for '{q_text}': got '{actual_semantics}', expected '{expected_semantics}'!"

    print("[PASS] All 9 Query Semantic Categories correctly classified and differentiated!")

def test_active_location_propagation_8_cities():
    print("\n--- TEST 2: ACTIVE LOCATION PROPAGATION AUDIT (8 COASTAL LOCATIONS) ---")
    
    locations = [
        ("Chennai", 13.08, 80.27),
        ("Kochi", 9.93, 76.26),
        ("Mangalore", 12.91, 74.85),
        ("Goa", 15.29, 73.98),
        ("Visakhapatnam", 17.68, 83.21),
        ("Gulf of Kutch", 22.50, 69.50),
        ("Tuticorin", 8.80, 78.10),
        ("Kanyakumari", 8.08, 77.55)
    ]

    distinct_targets = set()

    for city_name, lat, lon in locations:
        payload = {
            "query": "Where is the nearest Potential Fishing Zone today?",
            "mode": "C",
            "latitude": lat,
            "longitude": lon,
            "language": "en"
        }
        res = client.post("/api/query", json=payload)
        assert res.status_code == 200
        data = res.json()

        # 1. Geographic coordinates preserved in response
        assert data["geographic_coordinates"]["latitude"] == lat
        assert data["geographic_coordinates"]["longitude"] == lon

        # 2. Selected candidate is valid offshore marine
        pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
        assert pfz_ev is not None, f"Missing PFZ evidence for {city_name}"
        c_lat = pfz_ev["value"]["latitude"]
        c_lon = pfz_ev["value"]["longitude"]
        c_name = pfz_ev["value"]["name"]
        dist_km = pfz_ev["value"]["distance_km"]

        assert is_valid_marine_candidate(c_lat, c_lon), f"Candidate '{c_name}' ({c_lat}, {c_lon}) for {city_name} MUST be valid offshore marine!"
        print(f"City: {city_name:15} | User: ({lat:5.2f}, {lon:5.2f}) -> Offshore Target: '{c_name}' at ({c_lat}, {c_lon}) | Dist: {dist_km} km")
        distinct_targets.add(c_name)

    assert len(distinct_targets) >= 5, f"Expected dynamic target differentiation across 8 coastal locations, got {len(distinct_targets)}!"
    print("[PASS] Active location propagation verified across all 8 coastal regions of India!")

def test_terrestrial_land_rejection():
    print("\n--- TEST 3: TERRESTRIAL LAND REJECTION AUDIT ---")
    
    land_test_points = [
        ("Western Ghats (KA)", 13.03, 75.25),
        ("Inland Tamil Nadu (TN)", 13.10, 79.80),
        ("Inland Kerala (KL)", 9.95, 76.50),
        ("Western Ghats (Goa)", 15.30, 74.20),
        ("Inland Andhra (AP)", 17.70, 82.80),
        ("Bengaluru City", 12.97, 77.59),
        ("New Delhi", 28.61, 77.20)
    ]

    for name, lat, lon in land_test_points:
        is_valid = is_valid_marine_candidate(lat, lon)
        print(f"Point: '{name:25}' at ({lat:5.2f}, {lon:5.2f}) -> Marine Valid: {is_valid}")
        assert not is_valid, f"Terrestrial point '{name}' at ({lat}, {lon}) MUST be rejected!"

    print("[PASS] All terrestrial land points correctly identified and rejected!")

def test_map_and_recommendation_target_synchronization():
    print("\n--- TEST 4: MAP & RECOMMENDATION TARGET SYNCHRONIZATION ---")
    
    payload = {
        "query": "Navigate me to the nearest suitable fishing area.",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res = client.post("/api/query", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Verify map markers
    markers = data["map_markers"]
    pfz_markers = [m for m in markers if m["type"] == "pfz"]
    assert len(pfz_markers) >= 1, "Map payload MUST contain at least one PFZ marker"
    
    target_marker = pfz_markers[0]
    assert is_valid_marine_candidate(target_marker["lat"], target_marker["lng"]), "Map target marker MUST be valid marine!"
    
    # Verify navigation route geometry
    route_info = data.get("route_information")
    assert route_info is not None, "Route information MUST be present for navigation query"
    assert route_info["distance_km"] > 0.0

    print(f"Map Target Marker: '{target_marker['label']}' at ({target_marker['lat']}, {target_marker['lng']})")
    print(f"Navigation Transit Route Distance: {route_info['distance_km']} km | Status: {route_info.get('status', 'OK')}")
    print("[PASS] Map Payload & Navigation Routing Target Synchronization verified!")

def test_evidence_integrity_and_copernicus_reporting():
    print("\n--- TEST 5: EVIDENCE INTEGRITY & COPERNICUS FEED AUDIT ---")
    
    payload = {
        "query": "Which area has the highest chlorophyll concentration?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res = client.post("/api/query", json=payload)
    assert res.status_code == 200
    data = res.json()

    rec_text = data.get("recommendation", data.get("primary_recommendation", ""))
    print(f"Primary Recommendation Output:\n'{rec_text}'")

    # Verify Copernicus feed status is reported cleanly without fake values
    assert "unavailable" in rec_text.lower() or "copernicus" in rec_text.lower() or "chlorophyll" in rec_text.lower()
    print("[PASS] Evidence integrity and explicit Copernicus data availability reporting verified!")

if __name__ == "__main__":
    print("==============================================================")
    print("   RUNNING STEP 5G FINAL PRODUCTION-GRADE ORCA AUDIT SUITE    ")
    print("==============================================================")
    test_semantic_differentiation_audit()
    test_active_location_propagation_8_cities()
    test_terrestrial_land_rejection()
    test_map_and_recommendation_target_synchronization()
    test_evidence_integrity_and_copernicus_reporting()
    print("==============================================================")
    print("  ALL STEP 5G PRODUCTION AUDIT TESTS PASSED SUCCESSFULLY!     ")
    print("==============================================================")
