# AutoSage AI — Judge-facing pitch kit

## 20-second pitch

**AutoSage is an evidence-guided vehicle troubleshooting agent for two-wheelers and four-wheelers.** Instead of giving a generic chatbot answer, it plans a domain tool call, retrieves supporting technical knowledge, and generates a structured action guide with a deterministic safety gate.

## The hook

“Most people can describe that their vehicle feels wrong. They usually cannot translate that symptom into the right technical next step. AutoSage bridges that gap.”

## What makes it more than RAG

1. **Agentic planning:** the model decides whether a specialized vehicle tool is needed.
2. **Real tool execution:** OBD code lookup, safety gate, system triage, maintenance check, or parts-action planner.
3. **Evidence grounding:** the final answer uses retrieved research chunks with visible sources.
4. **Domain guardrail:** safety-sensitive patterns are handled by deterministic Python logic before the LLM writes the final response.
5. **Auditable UX:** the judge can open “Agent tool call” and see what actually happened.

## Best 3-minute live query

> My 2022 petrol Hyundai i20 shows P0420, the check-engine light is on, and the car feels mostly normal. What should I check, and do I need to replace anything?

### What to point at on screen

**1. Tool call**

`obd_code_lookup(P0420)`

Explain: “The agent recognized that a diagnostic code is present and called a specialized lookup tool.”

**2. RAG**

Show retrieved OBD/EPA and manufacturer guidance.

Explain: “The tool gives structured facts; RAG provides contextual evidence for the final explanation.”

**3. Design choice**

Say:

> “We deliberately separated safety-sensitive logic from generation. If a symptom looks dangerous, deterministic Python can escalate it even if the language model would otherwise produce a fluent but unsafe answer.”

**4. Final response**

Point out that AutoSage says the code narrows a system and does not automatically prove that the catalytic converter must be replaced.

## Likely judge questions

### Why RAG instead of just an LLM?

Vehicle guidance needs traceable evidence. RAG gives us a small, auditable domain corpus and lets the final answer point back to sources.

### Why not let the LLM do everything?

The LLM handles language and synthesis, but high-risk rules and structured lookups are more predictable as deterministic tools.

### Why Streamlit?

For a hackathon, Streamlit gives a very fast path from Python code to a shareable application. The UI is heavily customized with HTML/CSS, while the architecture remains modular enough to move to a React frontend later.

### How does it scale?

The next layer is a remote vector database, model-specific manual ingestion, an external cost/service API, and optional Bluetooth OBD-II input.

### How do you prevent hallucinated part replacement?

The system prompt explicitly requires “inspect/test before replacement”, the tool outputs are fed into the final prompt, and answers distinguish likely causes from confirmed faults.

## Stretch feature order

### Add first

- Hindi + English output toggle
- Dashboard-warning image upload
- Mechanic-ready report card
- Saved vehicle profile

### Add after that

- Live workshop/service lookup
- Cost ranges from a controlled regional dataset
- Personalized maintenance reminders

### Ambitious

- Bluetooth OBD-II adapter data
- Time-series sensor dashboard
- Manufacturer-specific manuals and service procedures

## Hinglish demo angle

AutoSage accepts natural Hinglish / Romanized Hindi, so the live demo can use a realistic Indian-user query without switching interfaces:

> **Meri 2022 petrol car mein P0420 aa raha hai, check-engine light on hai aur gaadi normally chal rahi hai. Kya check karna chahiye?**

The language selector supports Auto, Hinglish, English, and Hindi.

## New Product Feature: Safety-to-Service Handoff

AutoSage does not stop at “see a mechanic.” When a deterministic safety tool marks a problem HIGH/CRITICAL, the UI explicitly offers a **Nearby Mechanics** flow. Location permission is optional. The user can share device coordinates or enter an area/city/pincode; a real `find_nearby_mechanics` tool searches OpenStreetMap repair POIs, distance-sorts them, and returns a map plus directions links.

**Demo line:** “We designed the handoff so the AI doesn't secretly track location. The safety layer decides when professional help is appropriate; the user decides whether to share location; only then do we call the location tool.”
