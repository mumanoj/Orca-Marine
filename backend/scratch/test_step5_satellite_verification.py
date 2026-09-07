import sys
sys.path.insert(0, ".")
import asyncio
from app.tools.ocean_adapter import RealSatelliteTool

async def verify_satellite_tool():
    tool = RealSatelliteTool()
    print("\n=======================================================")
    print(" STEP 5: VERIFYING SATELLITE TOOL REAL & FALLBACK MODES")
    print("=======================================================")

    # Test 1: Real Satellite Query for Mangalore
    print("\n--- Test 1: Real Satellite Query for Mangalore (12.91, 74.85) ---")
    evidence = await tool.execute(latitude=12.91, longitude=74.85, timeout=10.0)
    for ev in evidence:
        print(f"\nParameter : {ev.parameter}")
        print(f"Value     : {ev.value} {ev.unit}")
        print(f"Status    : {ev.status}")
        print(f"Source    : {ev.source}")
        print(f"URL       : {ev.source_url}")

    # Test 2: Simulated Cloud Cover / Offline Fallback Test (broad search failure)
    print("\n--- Test 2: Deliberate Fallback Query (Unreachable Invalid Coordinates) ---")
    fallback_ev = await tool.execute(latitude=-89.99, longitude=-179.99, timeout=0.001)
    for ev in fallback_ev:
        print(f"\nParameter : {ev.parameter}")
        print(f"Value     : {ev.value} {ev.unit}")
        print(f"Status    : {ev.status}")
        print(f"Source    : {ev.source}")

if __name__ == "__main__":
    asyncio.run(verify_satellite_tool())
