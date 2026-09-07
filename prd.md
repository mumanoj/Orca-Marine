# ORCA — PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Project Name:** ORCA — Agentic AI Marine Intelligence Platform
**Project Type:** Agentic AI + Marine Intelligence + Geospatial Decision Support
**Target:** SIH / Hackathon MVP with a production-oriented architecture
**Document Status:** Master Product Requirements Document
**Version:** 1.0

---

# 1. PRODUCT VISION

ORCA is an **Agentic AI-powered conversational Marine Intelligence Platform** that enables fishermen, researchers, coastal authorities, maritime operators, travelers, and other marine stakeholders to interact with complex marine information using natural language.

ORCA must not merely retrieve information from individual APIs or datasets.

It must be capable of:

* understanding user intent
* decomposing complex queries
* dynamically selecting specialized agents
* selecting and invoking appropriate tools
* retrieving real marine, weather, satellite/EO and geospatial information
* correlating heterogeneous data
* performing spatial and temporal reasoning
* performing deterministic mathematical analysis
* assessing marine risk
* generating evidence-based recommendations
* explaining why a recommendation was produced
* visualizing results on a real interactive map
* identifying restricted/protected/geofenced areas
* calculating routes
* providing navigation handoff when appropriate
* maintaining contextual multi-turn conversations

The fundamental objective is:

> **Convert complex marine data into understandable, explainable and actionable decisions through collaborative AI agents.**

---

# 2. PROBLEM STATEMENT

Marine stakeholders depend on information from many independent sources:

* satellite Earth Observation
* sea surface temperature
* chlorophyll concentration
* potential fishing zone information
* weather forecasts
* oceanographic observations
* wave conditions
* tides
* marine advisories
* cyclone/lightning warnings
* GIS boundaries
* protected areas
* restricted waters
* maritime boundaries

These sources are heterogeneous and difficult for ordinary users to interpret and correlate.

ORCA should provide a conversational interface where a user can ask questions such as:

* "Where is the nearest Potential Fishing Zone today?"
* "Is it safe to venture into the sea tomorrow morning?"
* "What are the tide, weather and sea conditions near my fishing location?"
* "Are there any lightning or cyclone alerts in my area?"
* "Which regions have high chlorophyll and favourable SST?"
* "What is the safest route to a suitable fishing zone?"
* "Which areas should I avoid because of hazardous conditions or restrictions?"
* "Why has fish productivity declined in this region?"

---

# 3. CORE PRODUCT PRINCIPLES

ORCA must follow these principles.

## 3.1 Real Data First

Production responses must use real available APIs/datasets wherever possible.

Do not fabricate:

* weather
* ocean conditions
* satellite observations
* chlorophyll values
* SST values
* coordinates
* marine advisories
* boundaries
* routes
* safety measurements

Mock data may only be used in automated tests.

---

## 3.2 Evidence Before Recommendation

A recommendation must be derived from structured evidence.

The system should be able to answer:

> "Why did you make this recommendation?"

with actual data, not generic AI-generated reasoning.

---

## 3.3 LLM Is Not the Source of Truth

LLMs are reasoning and orchestration components.

They must not be treated as authoritative sources for:

* weather observations
* ocean measurements
* satellite observations
* coordinates
* marine warnings
* mathematical calculations
* safety scores
* GIS boundaries

Those must originate from real tools, APIs, datasets or deterministic calculations.

---

## 3.4 Deterministic Safety

Important numerical and safety calculations must be reproducible.

For identical inputs:

> Same inputs → same deterministic result.

LLM output must not arbitrarily change a deterministic safety calculation.

---

## 3.5 Graceful Degradation

If an API or LLM fails:

* report the failure
* use an appropriate fallback
* identify unavailable information
* never silently fabricate information

Missing data must never automatically become:

> "No warning."

or:

> "Safe."

---

# 4. THREE EXECUTION MODES

ORCA must support three execution modes.

These modes are a core product feature.

---

## MODE A — AGENTIC AI

### Purpose

Demonstrate genuine LLM-powered agentic intelligence.

### Behavior

Use:

* Groq as the primary LLM provider
* Gemini as the secondary/fallback provider
* dynamic planning
* LLM reasoning
* tool selection
* tool calling
* specialized agents
* agent collaboration
* real APIs
* evidence-based synthesis

The planner should dynamically determine which agents/tools are required.

The system must not execute every agent for every query.

---

## MODE B — RULE-BASED

### Purpose

Preserve the deterministic approach of the original ORCA MVP.

### Behavior

No LLM calls.

Absolutely no:

* Groq calls
* Gemini calls
* hidden LLM calls
* LLM-based intent parsing

Use:

* deterministic intent recognition
* deterministic task selection
* real APIs
* mathematical calculations
* geospatial computation
* deterministic thresholds
* deterministic risk scoring
* response templates

This mode must remain operational even when all LLM providers are unavailable.

---

## MODE C — HYBRID

### Purpose

Combine the strengths of both systems.

### Behavior

Use:

* LLM planning
* LLM reasoning
* LLM tool selection
* real APIs
* deterministic calculations
* GIS calculations
* risk engine
* verification

The LLM may propose a recommendation.

The deterministic system independently verifies important factual and safety conclusions.

If the two disagree, the discrepancy must be detected and handled according to the configured safety policy.

The LLM must never silently override deterministic safety constraints.

---

# 5. LLM PROVIDER REQUIREMENTS

## Primary

**Groq API**

Groq must be the default LLM provider.

## Secondary

**Google Gemini API**

Gemini must be supported as a fallback/secondary provider.

The application must use a provider abstraction.

Agents should not directly depend on Groq-specific or Gemini-specific implementation details.

Conceptually:

```text
Agent
  ↓
LLM Manager
  ↓
Primary Provider → Groq
  ↓
Fallback Provider → Gemini
```

API keys must exist only in server-side environment configuration.

Never expose them to the frontend.

---

# 6. AGENT ARCHITECTURE

ORCA should contain specialized agents.

Required conceptual agents:

1. User Interaction Agent
2. Planner / Reasoning Agent
3. Marine Data Discovery Agent
4. Weather Intelligence Agent
5. Ocean Analytics Agent
6. Satellite / Earth Observation Agent
7. Geospatial Agent
8. Risk / Safety Agent
9. Route / Navigation Agent
10. Final Response / Explanation Agent

These are logical responsibilities.

Implementation may combine or split internal classes/modules where technically justified.

However, the architecture must preserve these responsibilities.

---

# 7. GENUINE AGENTIC BEHAVIOR

A component should not be considered an agent merely because a file/class is named `WeatherAgent`.

A genuine agent must have:

* defined responsibility
* structured input
* structured output
* access to appropriate tools/data
* ability to determine whether its task is complete
* ability to report missing information
* ability to communicate results to the orchestrator

In Mode A/C, the system should demonstrate:

* planning
* reasoning
* tool selection
* task decomposition
* execution
* collaboration
* verification
* synthesis

---

# 8. ORCHESTRATOR REQUIREMENTS

The orchestrator is responsible for coordinating execution.

It must NOT use one fixed pipeline for every query.

Instead:

```text
User Query
   ↓
Planner
   ↓
Dynamic Task Plan
   ↓
Orchestrator
   ↓
Required Agents/Tools
   ↓
Evidence Collection
   ↓
Analysis
   ↓
Verification
   ↓
Recommendation
```

Example:

A simple weather query may require:

```text
Planner
 ↓
Weather Agent
 ↓
Final Response
```

A fishing safety/navigation query may require:

```text
Planner
 ↓
Marine Discovery
 ↓
Weather ─────────┐
Ocean ───────────┤
EO ──────────────┤
Geospatial ──────┤
                 ↓
              Risk
                 ↓
              Route
                 ↓
          Final Response
```

Independent tasks should execute concurrently where safe.

---

# 9. TOOL SYSTEM

The platform must implement a centralized tool registry.

Conceptual tools include:

```text
get_weather
get_marine_conditions
get_tide_conditions
get_marine_advisories
get_alerts
search_marine_data
get_satellite_data
get_sst
get_chlorophyll
geocode_location
reverse_geocode
calculate_distance
find_nearest_zone
check_geofence
check_protected_area
calculate_route
calculate_risk
```

Tools must return structured results.

LLMs must never invent tool results.

---

# 10. DATA SOURCE REQUIREMENTS

ORCA should support data from:

### Meteorological

* weather forecasts
* wind
* precipitation
* temperature
* severe weather
* lightning/cyclone alerts

### Oceanographic

* wave height
* wave period
* wave direction
* sea conditions
* tides where available
* ocean observations

### Earth Observation

* SST
* chlorophyll
* ocean productivity indicators
* potential fishing zone information where available

### GIS

* coastlines
* maritime boundaries
* protected marine areas
* restricted areas
* operational geofences

### Navigation

* route geometry
* distance
* estimated travel time
* route warnings

Providers must be configurable.

---

# 11. DATA PROVENANCE

Every important observation must contain:

```text
source
parameter
value
unit
latitude
longitude
observation/forecast timestamp
retrieval timestamp
data status
```

Possible status:

```text
observed
forecast
derived
estimated
unavailable
```

The user must be able to inspect the source of important information.

---

# 12. COMMON EVIDENCE MODEL

All agents should produce structured evidence.

Conceptually:

```text
Evidence
 ├── parameter
 ├── value
 ├── unit
 ├── source
 ├── location
 ├── observation_time
 ├── retrieved_at
 ├── status
 └── originating_agent
```

This evidence must be reusable by:

* risk engine
* explanation system
* frontend
* map
* audit trail
* admin dashboard

---

# 13. DECISION MODEL

Every major recommendation should produce a structured decision.

Conceptually:

```text
Decision
 ├── recommendation
 ├── rating
 ├── score
 ├── confidence
 ├── evidence
 ├── reasoning_factors
 ├── warnings
 ├── sources
 ├── coordinates
 ├── route
 ├── geofence_status
 └── verification_status
```

---

# 14. EXPLAINABLE AI

Explainability is a primary feature.

Every important recommendation should have two layers.

## Layer 1 — Simple Recommendation

Example:

> 🟢 Conditions appear suitable for the selected period.

## Layer 2 — Evidence / Why

Example:

```text
Wave height: 0.8 m
Wind speed: 11 km/h
Weather: Mostly clear
Marine advisory: No active warning detected
Safety score: 87/100
```

Then:

> These conditions resulted in the current recommendation.

The explanation must be generated from structured evidence.

Do not allow generic LLM reasoning to masquerade as factual evidence.

---

# 15. SAFETY ENGINE

The deterministic safety engine must consider configurable factors such as:

* wave height
* wind speed
* weather conditions
* severe weather
* marine advisories
* lightning/cyclone alerts
* restricted areas
* protected areas
* boundary proximity
* other relevant marine hazards

It should generate:

```text
score
rating
factor_scores
penalties
thresholds
explanation_factors
```

All thresholds must be documented and configurable.

---

# 16. FISHING-ZONE INTELLIGENCE

ORCA should support identifying suitable fishing zones based on available data.

Candidate evaluation may consider:

* chlorophyll
* SST
* PFZ information
* distance
* weather
* waves
* hazards
* restrictions
* protected areas
* geofences

The closest zone must not automatically be selected.

A farther zone may be preferred if it is significantly safer or more suitable.

The system must explain such decisions.

---

# 17. GEOSPATIAL REQUIREMENTS

The system must support real spatial calculations.

Required capabilities:

* coordinate handling
* distance calculations
* point-in-polygon
* nearest boundary
* polygon intersection
* geofence detection
* protected-area detection
* restricted-area detection
* zone ranking

No fake geographic boundaries in production mode.

---

# 18. REAL MAP REQUIREMENTS

The frontend must include a real interactive map.

Preferred:

* Leaflet
* OpenStreetMap

The map should display dynamically:

* current location
* recommended zones
* candidate zones
* hazardous areas
* protected areas
* restricted areas
* maritime boundaries
* routes
* relevant satellite/EO layers
* relevant marine/weather overlays

Map content must come from backend data.

---

# 19. NAVIGATION

When ORCA identifies a recommended destination:

The user should be able to:

1. see the destination on the map
2. see distance
3. request a route
4. see route geometry
5. see estimated travel time
6. see route warnings
7. hand off to navigation/maps where appropriate

ORCA must not provide navigation into:

* prohibited areas
* restricted waters
* protected zones where navigation is not permitted
* explicitly hazardous destinations

---

# 20. TWO-LANGUAGE SUPPORT

Initial language support:

1. English
2. Hindi

The system should:

* detect user language
* accept queries in either language
* respond in the user's language
* preserve conversational context
* allow language switching

Internal structured data remains language-independent.

The architecture must allow additional Indian languages to be added later.

---

# 21. MULTI-TURN CONVERSATION

ORCA must understand contextual follow-up questions.

Example:

User:

> "How is the sea tomorrow?"

Then:

> "What about near Mangalore?"

The second query should modify the relevant location/context rather than being treated as a completely unrelated question.

Maintain structured conversational context including:

* intent
* location
* time
* selected zone
* relevant previous entities
* language
* execution mode

---

# 22. USER INTERFACE

The primary UI should contain:

### Chat

Natural-language conversation.

### Map

Real geospatial visualization.

### Execution Mode

Three buttons:

```text
A — Agentic AI
B — Rule-Based
C — Hybrid
```

### Explanation Panel

"Why did ORCA make this decision?"

### Evidence

Facts, values, sources and timestamps.

### Warnings

Hazards and restrictions.

### Navigation

Route and destination actions when applicable.

---

# 23. LIVE AGENT EXECUTION

During a query, show actual execution progress.

Example:

```text
Understanding request...
Planning tasks...
Searching marine data...
Checking weather...
Analyzing ocean conditions...
Checking satellite data...
Checking boundaries...
Calculating risk...
Verifying recommendation...
Preparing response...
```

These states must correspond to actual backend execution events.

Do not use a fake loading animation pretending that agents are running.

---

# 24. ADMIN / DEMONSTRATION DASHBOARD

An admin dashboard should visualize:

* user query
* selected mode
* planner
* agents
* tools
* API calls
* execution states
* evidence
* deterministic verification
* final recommendation

The agent graph must represent actual execution.

If an agent was not required:

> Skipped / Not Required

If it failed:

> Failed

If it ran:

> Completed

Parallel execution should be visually distinguishable.

---

# 25. EXECUTION TRACE

For each query, record a structured execution trace.

Include:

```text
query
mode
language
plan
agents_executed
tools_executed
timestamps
latency
errors
LLM provider
evidence
deterministic calculations
verification
final recommendation
```

Never store secrets.

---

# 26. API FAILURE BEHAVIOR

If an API fails:

1. retry when appropriate
2. use configured fallback when available
3. mark data unavailable if necessary
4. continue only when the remaining evidence is sufficient
5. clearly communicate limitations

Never replace missing data with fabricated values.

---

# 27. LLM FAILURE BEHAVIOR

If Groq fails:

* attempt Gemini when configured

If both fail:

* Mode B must continue working
* Mode A must clearly report that LLM functionality is unavailable
* Mode C must follow configured fallback/verification policy

The system must not silently switch execution modes without informing the user.

---

# 28. SECURITY REQUIREMENTS

Must include:

* environment-based secrets
* no API keys in frontend
* `.env` ignored by Git
* secure password hashing
* JWT authentication
* protected admin routes
* input validation
* CORS configuration
* appropriate rate limiting
* no sensitive information in logs

---

# 29. PERFORMANCE REQUIREMENTS

Use asynchronous operations.

Independent API/agent calls should run concurrently where safe.

Examples:

Weather and Ocean retrieval can often execute concurrently.

The system should record:

* agent latency
* tool latency
* API latency
* total query latency

---

# 30. ERROR TRANSPARENCY

Never silently fail.

The system should explicitly distinguish:

```text
success
partial_success
unavailable
failed
```

For safety-critical queries, insufficient evidence must result in:

> "I cannot provide a reliable safety recommendation because required data is unavailable."

rather than an invented recommendation.

---

# 31. DEMONSTRATION QUERIES

The final application must support workflows for:

1. Is it safe to venture into the sea tomorrow morning?
2. Where is the nearest suitable fishing zone?
3. Which region has high chlorophyll and favorable SST?
4. What are the tide, weather and sea conditions near my fishing location?
5. Are there lightning or cyclone alerts in my area?
6. What is the safest route to the recommended fishing zone?
7. Which areas should be avoided because of hazardous conditions or restrictions?
8. Why has fish productivity declined in this coastal region?

The exact agent execution should be determined dynamically.

---

# 32. ARCHITECTURAL NON-NEGOTIABLES

The implementation must NOT:

* create fake agents
* create fake API responses
* hardcode marine measurements
* hardcode satellite results
* hardcode route results
* hardcode geographic boundaries
* pretend a normal function is an autonomous agent
* make every query execute every agent
* allow LLMs to invent tool results
* allow missing data to become "safe"
* expose API keys
* create separate incompatible response formats for A/B/C

---

# 33. ACCEPTANCE CRITERIA

ORCA is considered functionally successful only when this workflow works:

```text
User
 ↓
Natural-language query
 ↓
Language detection
 ↓
Planner
 ↓
Dynamic execution plan
 ↓
Orchestrator
 ↓
Specialized agents
 ↓
Real tools/APIs
 ↓
Evidence
 ↓
Spatial/temporal reasoning
 ↓
Deterministic verification
 ↓
Recommendation
 ↓
Explainable evidence
 ↓
Map visualization
 ↓
Navigation when appropriate
```

The exact path must change according to the query.

---

# 34. FINAL PRODUCT PRINCIPLE

ORCA must demonstrate that **Agentic AI is being used to coordinate real marine intelligence workflows**, rather than merely using an LLM to generate conversational text.

The system should combine:

> **LLM reasoning + autonomous orchestration + real APIs + Earth Observation + GIS + deterministic mathematics + safety verification + explainability + interactive maps + navigation.**

The product should remain useful even when the LLM is unavailable.

The final result must be understandable to ordinary marine users while still exposing sufficient evidence and technical information for researchers, authorities and SIH judges.

---

# 35. IMPLEMENTATION PRIORITY

When making engineering decisions, prioritize in this order:

1. Correctness
2. Real agent behavior
3. Real data/API integration
4. Safety and deterministic verification
5. Evidence and explainability
6. Geospatial correctness
7. A/B/C mode correctness
8. Conversational quality
9. Map/navigation experience
10. Visual polish

Never sacrifice correctness merely to make the UI appear complete.
