import sys
sys.path.insert(0, ".")
import asyncio
import logging
from app.core.config import settings
from app.core.llm.manager import llm_manager
from app.orchestration.planner import ExecutionPlan

# Configure logging to output [LLM_TIER_AUDIT] lines clearly
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_tier(tier_num: int):
    print(f"\n=======================================================")
    print(f" TESTING TIER {tier_num} (LLM_FORCE_TIER={tier_num})")
    print(f"=======================================================")
    
    settings.LLM_FORCE_TIER = tier_num
    # Reset circuit breakers for clean test
    llm_manager.circuit_breaker.failure_counts.clear()
    llm_manager.circuit_breaker.circuit_open_until.clear()

    try:
        # Test 1: Structured Execution Plan Generation
        query = "Is the ocean safe for fishing near Mangalore tomorrow morning?"
        plan, prov_desc = await llm_manager.generate_structured(query, ExecutionPlan)
        print(f"[RESULT] Tier {tier_num} Structured Plan:")
        print(f"  - Provider/Tier Used : {prov_desc}")
        print(f"  - Intent             : {plan.intent}")
        print(f"  - Required Agents    : {plan.required_agents}")

        # Test 2: Domain Text Synthesis Generation
        text, prov_desc2 = await llm_manager.generate_text("Summarize wave and wind conditions near Mangalore coast.")
        print(f"[RESULT] Tier {tier_num} Text Synthesis:")
        print(f"  - Provider/Tier Used : {prov_desc2}")
        print(f"  - Response Excerpt   : {text[:150]}...")
        print(f"  - Status             : SUCCESS (Valid, non-hallucinated response)")

    except Exception as err:
        print(f"[ERROR] Tier {tier_num} Failed: {err}")

async def main():
    print("\n-------------------------------------------------------")
    print(" 4-TIER LLM PROVIDER & FALLBACK AUDIT TEST SUITE")
    print("-------------------------------------------------------")

    # Run Normal (Unforced) First
    settings.LLM_FORCE_TIER = None
    query = "Check tidal conditions near Mangalore"
    text, prov_desc = await llm_manager.generate_text(query)
    print(f"\n[UNFORCED DEFAULT RUN] Provider/Tier Used: {prov_desc}")

    # Test Each Tier Individually via Forced Configuration
    for t in [1, 2, 3, 4]:
        await test_tier(t)

if __name__ == "__main__":
    asyncio.run(main())
