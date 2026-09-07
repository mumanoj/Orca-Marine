"""
ORCA Step 5E Semantic Marine Intelligence & Dynamic Ranking Test Suite
Validates:
1. All 11 Semantic Query Categories (NEAREST_ZONE, HIGHEST_CHLOROPHYLL, HIGHEST_PRODUCTIVITY, 
   SUITABLE_NEARBY_ZONES, PRODUCTIVITY_CAUSE, AVOIDANCE, ROUTING, WEATHER_INFO, OCEAN_STATE, 
   HAZARD_ADVISORY, SAFETY_ASSESSMENT).
2. Multi-Candidate Ranking differentiation (Highest Productivity vs Nearest vs Chlorophyll).
3. Absolute Evidence Integrity (unavailable chlorophyll reported cleanly, no fabricated 1.2 mg/m³ values).
4. Natural Fisherman Language (Terminology compliance: no 'fishing ground' unless present in user query).
5. Map markers payload matching query semantics.
"""
import sys
import asyncio, os
from pathlib import Path

backend_dir = Path(r"c:\Local disk D\OneDrive\Desktop\orca final\backend")
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.orchestration.planner import planner_agent
from app.tools.pfz_adapter import RealPFZTool, REGIONAL_PFZ_CANDIDATES
from app.tools.registry import tool_registry

client = TestClient(app)

def test_11_semantic_categories():
    print("\n--- TEST 1: 11 SEMANTIC QUERY CATEGORIES CLASSIFICATION ---")
    queries_map = {
        "Where is the nearest Potential Fishing Zone today?": "NEAREST_ZONE",
        "Which area has the highest chlorophyll concentration?": "HIGHEST_CHLOROPHYLL",
        "Where is the most productive fishing area near me?": "HIGHEST_PRODUCTIVITY",
        "Show me promising fishing areas nearby.": "SUITABLE_NEARBY_ZONES",
        "Why has fishing productivity decreased in this region?": "PRODUCTIVITY_CAUSE",
        "Which fishing zones should I avoid today?": "AVOIDANCE",
        "Navigate me to the nearest suitable fishing area.": "ROUTING",
        "What is the weather forecast for tomorrow morning?": "WEATHER_INFO",
        "How rough are the sea waves right now?": "OCEAN_STATE",
        "Are there any cyclone or lightning alerts in my area?": "HAZARD_ADVISORY",
        "Is it safe to venture into the sea tomorrow morning?": "SAFETY_ASSESSMENT"
    }

    for query, expected_sem in queries_map.items():
        plan = planner_agent.plan_mode_b(query, latitude=12.91, longitude=74.85, language="en")
        sem = plan.query_semantics
        print(f"Query: '{query}' -> Detected Semantics: '{sem}' (Expected: '{expected_sem}')")
        assert sem == expected_sem, f"Failed for query '{query}': got {sem}, expected {expected_sem}"

    print("[PASS] All 11 Semantic Query Categories correctly classified!")

def test_multi_candidate_pfz_ranking():
    print("\n--- TEST 2: MULTI-CANDIDATE PFZ RANKING DIFFERENTIATION ---")
    tool = RealPFZTool()
    
    # Run ranking for NEAREST_ZONE
    ev_nearest = asyncio.run(tool.execute(12.91, 74.85, query="nearest fishing zone", query_semantics="NEAREST_ZONE"))
    pfz_near = next(e for e in ev_nearest if e.parameter == "nearest_potential_fishing_zone")
    ranked_near = next(e for e in ev_nearest if e.parameter == "ranked_pfz_candidates")

    # Run ranking for HIGHEST_PRODUCTIVITY
    ev_best = asyncio.run(tool.execute(12.91, 74.85, query="most productive fishing area", query_semantics="HIGHEST_PRODUCTIVITY"))
    pfz_best = next(e for e in ev_best if e.parameter == "nearest_potential_fishing_zone")

    print(f"Nearest Selected Zone: '{pfz_near.value['name']}' (Dist: {pfz_near.value['distance_km']} km)")
    print(f"Best Productivity Selected Zone: '{pfz_best.value['name']}' (Score: {pfz_best.value['productivity_score']})")
    
    assert pfz_near.value["name"] != pfz_best.value["name"], "Nearest and Best Productivity should differentiate candidates!"
    assert len(ranked_near.value["top_candidates"]) >= 3, "Multi-candidate list must include top candidates"
    print("[PASS] Multi-Candidate Ranking differentiation verified!")

def test_evidence_integrity_and_terminology():
    print("\n--- TEST 3: ABSOLUTE EVIDENCE INTEGRITY & TERMINOLOGY ---")
    
    # 1. Chlorophyll Unavailability Integrity
    payload_chlo = {
        "query": "Which area has the highest chlorophyll concentration?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res_chlo = client.post("/api/query", json=payload_chlo)
    assert res_chlo.status_code == 200
    data_chlo = res_chlo.json()
    
    rec_chlo = data_chlo["recommendation"]
    print(f"Chlorophyll Query Recommendation: '{rec_chlo}'")
    assert "1.2 mg/m³" not in rec_chlo, "Must NOT fabricate 1.2 mg/m³ chlorophyll when unavailable!"
    
    # 2. Terminology Rule: Avoid 'fishing ground' unless in user query
    payload_term = {
        "query": "Where is the best fishing location near me?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res_term = client.post("/api/query", json=payload_term)
    assert res_term.status_code == 200
    data_term = res_term.json()
    
    rec_term = data_term["recommendation"]
    print(f"Best Fishing Query Recommendation: '{rec_term}'")
    assert "fishing ground" not in rec_term.lower(), "Must NOT use 'fishing ground' when user did not use it!"

    # 3. Productivity Cause Question must NOT force single location as primary recommendation
    payload_cause = {
        "query": "Why has fishing productivity decreased in this region?",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res_cause = client.post("/api/query", json=payload_cause)
    assert res_cause.status_code == 200
    data_cause = res_cause.json()
    
    rec_cause = data_cause["recommendation"]
    print(f"Productivity Cause Recommendation: '{rec_cause}'")
    assert any(w in rec_cause.lower() for w in ["temperature", "upwelling", "driven", "anomalies", "productivity"]), "Productivity cause must provide causal explanation!"
    
    print("[PASS] Absolute Evidence Integrity & Natural Fisherman Language verified!")

def test_explainability_and_map_payload():
    print("\n--- TEST 4: EXPLAINABILITY FACTORS & MAP PAYLOAD ---")
    payload = {
        "query": "Show me promising fishing areas nearby.",
        "mode": "C",
        "latitude": 12.91,
        "longitude": 74.85,
        "language": "en"
    }
    res = client.post("/api/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    
    # Verify ORCA Decision Criterion explainability factor
    factors = data["explainability_factors"]
    strat_factor = next((f for f in factors if f["category"] == "strategy"), None)
    assert strat_factor is not None, "ORCA Decision Criterion strategy factor must be present"
    print(f"Decision Criterion Factor: '{strat_factor['value']}'")

    # Verify map markers
    markers = data["map_markers"]
    print(f"Map Markers Count: {len(markers)}")
    assert len(markers) >= 3, "SUITABLE_NEARBY_ZONES must provide multiple candidate map markers"

    print("[PASS] Explainability Factors & Map Payload verified!")

if __name__ == "__main__":
    print("==============================================================")
    print("   RUNNING STEP 5E SEMANTIC & EVIDENCE INTEGRITY ACCEPTANCE   ")
    print("==============================================================")
    test_11_semantic_categories()
    test_multi_candidate_pfz_ranking()
    test_evidence_integrity_and_terminology()
    test_explainability_and_map_payload()
    print("==============================================================")
    print("  ALL STEP 5E ACCEPTANCE TESTS PASSED SUCCESSFULLY!       ")
    print("==============================================================")
