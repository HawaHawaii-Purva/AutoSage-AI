---
title: AutoSage AI
emoji: 🚘
colorFrom: indigo
colorTo: blue
sdk: streamlit
app_file: app.py
---

# AutoSage AI 🚘

**Evidence-guided vehicle troubleshooting for 2-wheelers and 4-wheelers.**

AutoSage is a hackathon-ready AI vehicle assistant that combines:

- **RAG** over a curated vehicle safety/troubleshooting corpus
- **LLM agent planning**
- **Deterministic domain tools** for OBD codes, safety gating, symptom triage, maintenance and parts-action planning
- **A safety-first response policy** that distinguishes likely causes from confirmed diagnosis
- **English + Hinglish + Hindi support** with automatic Hinglish/Roman-Hindi detection
- **Streamlit UI** with an auditable agent trace and research-source view

## Architecture

```text
User
  ↓
Streamlit UI
  ↓
Agent planner (LLM)
  ↓
Tool call
  ├── OBD code lookup
  ├── Safety gate
  ├── Symptom/system triage
  ├── Maintenance check
  └── Parts action plan
  ↓
Chroma RAG retrieval
  ↓
LLM synthesis
  ↓
Structured troubleshooting guide + sources + trace
```

## Multilingual / Hinglish UX

AutoSage accepts natural-language input in English, Hindi, and Hinglish (Romanized Hindi). The UI offers **Auto / Hinglish / English / Hindi** response modes. In Auto mode, a lightweight heuristic detects common Roman-Hindi markers and tells the LLM to answer in a matching Hinglish style. This is not a translation layer: it preserves technical terms such as OBD-II, P0420, ABS, brake pad, and oxygen sensor.

Example input:

> **Meri 2022 petrol car mein P0420 aa raha hai, check-engine light on hai aur gaadi normally chal rahi hai. Kya check karna chahiye?**

## Deliberate design decision

**Safety-sensitive logic is deterministic.** The LLM can interpret and explain a vehicle symptom, but a plain-Python safety tool is used to flag obvious high-risk patterns. The final model prompt is required to respect the tool result and escalate rather than suggest risky experimentation.

## Local setup (VS Code)

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Install packages

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Make sure Ollama is running

Example model:

```bash
ollama pull llama3.2:3b
ollama list
```

### 4. Create `.env`

Copy `.env.example` to `.env`.

Default local settings:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### 5. Run

```bash
streamlit run app.py
```

## Best demo query

Use a real tool call that judges can see:

> **My 2022 petrol Hyundai i20 shows P0420, the check-engine light is on, and the car feels mostly normal. What should I check, and do I need to replace anything?**

Expected path:

```text
LLM planner
   ↓
obd_code_lookup(P0420)
   ↓
Chroma retrieves OBD + manufacturer guidance
   ↓
LLM synthesizes diagnosis guide
   ↓
UI shows tool trace + sources
```

## 3-minute live demo script

**0:00–0:25 — Problem**

“Vehicle problems are often described in natural language, while useful troubleshooting information is scattered across manuals and technical resources. AutoSage turns that into an evidence-guided workflow.”

**0:25–0:50 — Show UI**

Select four-wheeler, enter vehicle details, enter the P0420 query.

**0:50–1:30 — Run diagnosis**

Point to the agent trace: the planner selected `obd_code_lookup`, the tool returned the generic meaning and checks, and RAG retrieved supporting material.

**1:30–2:15 — Explain result**

Show that the answer does not blindly say “replace catalytic converter”. It recommends diagnosis first, lists checks, and explains that a DTC narrows the system but does not prove a failed part.

**2:15–2:45 — Design decision**

“We deliberately made the safety gate deterministic. The LLM handles language, but high-risk vehicle patterns are handled by testable Python logic before the final response.”

**2:45–3:00 — Close**

“The same architecture can extend to live service pricing, image-based inspection, OBD-II hardware input, service history and personalized maintenance.”

## Cloud deployment: Streamlit Community Cloud

1. Push this project to a **public GitHub repository**.
2. Go to Streamlit Community Cloud and connect GitHub.
3. Create an app from the repository and select `app.py`.
4. Add the secret:

```toml
LLM_PROVIDER = "hf"
HF_TOKEN = "hf_your_token_here"
HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"
```

Do **not** commit the Hugging Face token to GitHub.

Community Cloud can deploy directly from a GitHub repository, and repository changes can trigger updated deployments. See the official Streamlit deployment documentation.

## GitHub commands

```bash
git init
git add .
git commit -m "Initial AutoSage AI hackathon build"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/AutoSage-AI.git
git push -u origin main
```

## Recommended stretch features

### Tier 1 — high value / low complexity

- Voice symptom input
- Saved vehicle profiles
- Conversation history
- Multilingual Hindi/English mode
- “Mechanic-ready report” export

### Tier 2 — wow factor

- Upload a dashboard-warning photo
- Upload a visible part/tyre/brake photo
- Interactive vehicle health timeline
- Personalized maintenance reminders
- Service-cost estimates from a controlled dataset

### Tier 3 — ambitious

- Bluetooth OBD-II adapter integration
- Live scan-data dashboard
- Nearby workshop search
- Parts catalogue integration
- Manufacturer/model-specific manual retrieval

## Safety boundary

AutoSage is a prototype decision-support system. It should not be presented as a certified mechanic or as a substitute for an owner's manual, qualified technician, diagnostic equipment, or emergency/roadside assistance.

## Research references

- NHTSA Tire Safety: https://www.nhtsa.gov/vehicle-safety/tires
- Motorcycle Safety Foundation T-CLOCS: https://msf-usa.org/documents/library/t-clocs-pre-ride-inspection-checklist/
- U.S. EPA OBD resources: https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100LW9G.TXT
- Hyundai Owner's Manuals: https://ownersmanual.hyundai.com/
- Gradio / Hugging Face Spaces docs: https://huggingface.co/docs/hub/spaces-overview
- Streamlit Community Cloud docs: https://docs.streamlit.io/deploy/streamlit-community-cloud

## Nearby Mechanic Finder (New)

When AutoSage detects a higher-risk symptom, it recommends professional inspection. The user can then open **Nearby Mechanics** and either:

1. Share browser/device location (optional), or
2. Enter an area, city, or pincode.

The `find_nearby_mechanics` tool queries OpenStreetMap's Overpass API for nearby vehicle-repair POIs, sorts them by distance, and displays them on a map with links for directions. The location flow is explicit and user-controlled; AutoSage does not persist a location database.

This uses the public OpenStreetMap Nominatim geocoder only for a user-triggered area lookup, with an identifiable User-Agent and a switchable endpoint. Keep traffic low and cache/replace the service if your usage grows. See the OpenStreetMap Foundation Nominatim policy: https://operations.osmfoundation.org/policies/nominatim/
