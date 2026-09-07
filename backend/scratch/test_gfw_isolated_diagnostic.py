import sys
sys.path.insert(0, ".")
import asyncio
import httpx
from app.core.config import settings
from app.services.gfw_service import GFWService, GFWDataUnavailableError

async def test_gfw_isolated_real_data():
    print("=======================================================================")
    print("       ISOLATED REAL-DATA AUTHENTICATED GFW API TEST                   ")
    print("=======================================================================")
    
    key_configured = bool(settings.GFW_API_KEY)
    print(f"GFW_API_KEY Configured in Environment : {key_configured}")
    if not key_configured:
        print("FAIL: GFW_API_KEY is not configured in .env!")
        return False

    service = GFWService()
    # Coastal coordinates near Mangalore (12.91, 74.85)
    lat, lon = 12.91, 74.85
    print(f"Executing GFW API request for coordinates ({lat}, {lon})...")
    
    try:
        evidence = await service.get_fishing_activity(lat, lon)
        print(f"\nSUCCESS! Real GFW Data Retrieved:")
        print(f"  Source Name         : {evidence.source}")
        print(f"  Source Type         : {evidence.source_type}")
        print(f"  Parameter           : {evidence.parameter}")
        print(f"  Status              : {evidence.status}")
        print(f"  Observed Hours      : {evidence.value.get('total_fishing_hours')}")
        print(f"  Observed Vessels    : {evidence.value.get('observed_vessel_count')}")
        return True
    except GFWDataUnavailableError as e:
        print(f"\nREAL DATA RETRIEVAL UNABLE TO COMPLETE:")
        print(f"  Error Type : GFWDataUnavailableError")
        print(f"  Message    : {e}")
        return False
    except Exception as e:
        print(f"\nREAL DATA RETRIEVAL FAILED WITH UNEXPECTED ERROR:")
        print(f"  Error Type : {type(e).__name__}")
        print(f"  Message    : {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gfw_isolated_real_data())
    sys.exit(0 if success else 1)
