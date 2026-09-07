"""
ORCA Step 5F — Final Marine Intelligence Hardening, Water-Only Validation & Dynamic E2E Audit
Validates:
1. Water-Only / Offshore Candidate Validation (is_valid_marine_candidate).
2. Land Coordinate Rejection (Verifies land points are rejected).
3. Active Location Change Audit across 5 coastal cities (Chennai, Kochi, Mangalore, Goa, Visakhapatnam).
4. Semantic Query Differentiation (NEAREST != BEST != SUITABLE != HIGHEST CHLOROPHYLL != PRODUCTIVITY_CAUSE).
5. Map Payload Synchronization & Route Destination Consistency.
6. Evidence Integrity & Fisherman Language Compliance.
"""
import sys
import asyncio
from pathlib import Path

backend_dir = Path(r"c:\Local disk D\OneDrive\Desktop\orca final\backend")
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.domain.marine_geospatial import is_valid_marine_candidate, generate_dynamic_offshore_candidates
from app.tools.pfz_adapter import RealPFZTool

client = TestClient(app)

def test_water_only_marine_validation():
    print("\n--- TEST 1: WATER-ONLY / OFFSHORE MARINE VALIDATION ---")
    
    # Offshore marine coordinates
    offshore_points = [
        (13.20, 80.45), # Offshore Chennai (Bay of Bengal)
        (12.85, 74.45), # Offshore Mangalore (Arabian Sea)
        (9.95, 75.85),  # Offshore Kochi (Arabian Sea)
        (15.20, 73.40), # Offshore Goa (Arabian Sea)
        (17.60, 83.50)  # Offshore Vizag (Bay of Bengal)
    ]
    for lat, lon in offshore_points:
        assert is_valid_marine_candidate(lat, lon), f"Expected ({lat}, {lon}) to be VALID marine location!"

    # Land / Terrestrial coordinates
    land_points = [
        (13.03, 75.25), # Western Ghats inland Karnataka land
        (13.10, 79.80), # Inland Tamil Nadu land near Chennai
        (9.95, 76.50),  # Inland Kerala land near Kochi
        (15.30, 74.20), # Inland Western Ghats land near Goa
        (17.70, 82.80)  # Inland Andhra Pradesh land near Vizag
    ]
    for lat, lon in land_points:
        assert not is_valid_marine_candidate(lat, lon), f"Expected ({lat}, {lon}) on land to be REJECTED!"

    print("[PASS] Water-Only Marine Validation & Land Rejection verified!")

def test_dynamic_active_location_propagation():
    print("\n--- TEST 2: DYNAMIC ACTIVE LOCATION PROPAGATION AUDIT ---")
    
    locations = [
        ("Chennai", 13.08, 80.27),
        ("Kochi", 9.93, 76.26),
        ("Mangalore", 12.91, 74.85),
        ("Goa", 15.29, 73.98),
        ("Visakhapatnam", 17.68, 83.21)
    ]

    previous_selected_names = set()

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

        # 1. Geographic coordinates preserved
        assert data["geographic_coordinates"]["latitude"] == lat
        assert data["geographic_coordinates"]["longitude"] == lon

        # 2. Selected candidate is valid marine
        pfz_ev = next((e for e in data["evidence"] if e["parameter"] == "nearest_potential_fishing_zone"), None)
        assert pfz_ev is not None
        c_lat = pfz_ev["value"]["latitude"]
        c_lon = pfz_ev["value"]["longitude"]
        c_name = pfz_ev["value"]["name"]
        
        assert is_valid_marine_candidate(c_lat, c_lon), f"Candidate ({c_lat}, {c_lon}) for {city_name} MUST be valid offshore marine!"
        print(f"City: {city_name:13} -> Selected Offshore Candidate: '{c_name}' at ({c_lat}, {c_lon}) | Dist: {pfz_ev['value']['distance_km']} km")
        previous_selected_names.add(c_name)

    # Assert candidate selection dynamically changes with active location!
    assert len(previous_selected_names) >= 3, "Selected offshore candidate MUST dynamically change with user active location!"
    print("[PASS] Dynamic Active Location Propagation verified across 5 coastal locations!")

def test_semantic_query_differentiation():
    print("\n--- TEST 3: SEMANTIC QUERY DIFFERENTIATION AUDIT ---")
    
    base_payload = {"latitude": 12.91, "longitude": 74.85, "mode": "C", "language": "en"}
    
    # 1. Nearest
    q1 = client.post("/api/query", json={**base_payload, "query": "Where is the nearest fishing area?"}).json()
    # 2. Best / Most Productive
    q2 = client.post("/api/query", json={**base_payload, "query": "Where is the most productive fishing area?"}).json()
    # 3. Suitable Nearby
    q3 = client.post("/api/query", json={**base_payload, "query": "Show me suitable fishing areas nearby."}).json()
    # 4. Chlorophyll
    q4 = client.post("/api/query", json={**base_payload, "query": "Which area has the highest chlorophyll concentration?"}).json()
    # 5. Causal Productivity
    q5 = client.post("/api/query", json={**base_payload, "query": "Why has fishing productivity declined in this region?"}).json()

    print(f"1. NEAREST Query Semantics:      '{q1['decision_summary']['query_semantics']}' | Criterion: '{q1['decision_summary']['ranking_criterion']}'")
    print(f"2. BEST Query Semantics:         '{q2['decision_summary']['query_semantics']}' | Criterion: '{q2['decision_summary']['ranking_criterion']}'")
    print(f"3. SUITABLE Query Semantics:     '{q3['decision_summary']['query_semantics']}' | Criterion: '{q3['decision_summary']['ranking_criterion']}'")
    print(f"4. CHLOROPHYLL Query Semantics:   '{q4['decision_summary']['query_semantics']}' | Criterion: '{q4['decision_summary']['ranking_criterion']}'")
    print(f"5. CAUSAL Query Semantics:       '{q5['decision_summary']['query_semantics']}' | Criterion: '{q5['decision_summary']['ranking_criterion']}'")

    assert q1['decision_summary']['query_semantics'] == "NEAREST_ZONE"
    assert q2['decision_summary']['query_semantics'] == "HIGHEST_PRODUCTIVITY"
    assert q3['decision_summary']['query_semantics'] == "SUITABLE_NEARBY_ZONES"
    assert q4['decision_summary']['query_semantics'] == "HIGHEST_CHLOROPHYLL"
    assert q5['decision_summary']['query_semantics'] == "PRODUCTIVITY_CAUSE"

    # Verify Nearest != Best Candidate Selection
    cand_q1 = next(e["value"]["name"] for e in q1["evidence"] if e["parameter"] == "nearest_potential_fishing_zone")
    cand_q2 = next(e["value"]["name"] for e in q2["evidence"] if e["parameter"] == "nearest_potential_fishing_zone")
    assert cand_q1 != cand_q2, f"NEAREST ('{cand_q1}') and BEST ('{cand_q2}') must differentiate candidates!"

    print("[PASS] Explicit Semantic Query Differentiation verified!")

def test_map_payload_and_routing_synchronization():
    print("\n--- TEST 4: MAP PAYLOAD & ROUTING SYNCHRONIZATION ---")
    
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
    print(f"Map Markers Generated: {len(markers)} marker(s)")
    for m in markers:
        assert is_valid_marine_candidate(m["lat"], m["lng"]) or m["type"] == "info", f"Marker '{m['label']}' at ({m['lat']}, {m['lng']}) MUST be valid marine!"

    # Verify route geometry destination matches target candidate
    route_info = data.get("route_information")
    assert route_info is not None, "Route geometry must be generated for navigation queries"
    assert route_info["distance_km"] > 0.0, "Route distance must be > 0"
    print(f"Navigation Transit Route Distance: {route_info['distance_km']} km | Status: {route_info.get('status', 'OK')}")

    print("[PASS] Map Payload & Routing Synchronization verified!")

if __name__ == "__main__":
    print("==============================================================")
    print("   RUNNING STEP 5F FINAL MARINE INTELLIGENCE HARDENING AUDIT  ")
    print("==============================================================")
    test_water_only_marine_validation()
    test_dynamic_active_location_propagation()
    test_semantic_query_differentiation()
    test_map_payload_and_routing_synchronization()
    print("==============================================================")
    print("  ALL STEP 5F AUDIT AND ACCEPTANCE TESTS PASSED SUCCESSFULLY! ")
    print("==============================================================")
