from __future__ import annotations

import os
import time
import html
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from streamlit_geolocation import streamlit_geolocation
from agent import analyze
from tools import find_nearby_mechanics, geocode_location

# Streamlit Cloud secrets are copied into the environment for local/cloud parity.
try:
    for _key in (
        "LLM_PROVIDER", "HF_TOKEN", "HF_MODEL", "OLLAMA_MODEL", "OLLAMA_BASE_URL",
        "OSM_USER_AGENT", "OSM_NOMINATIM_URL", "OVERPASS_URL",
    ):
        if _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass

st.set_page_config(
    page_title="AutoSage AI — Vehicle Intelligence",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --bg:#070914; --panel:#0d1222; --panel2:#11172b; --line:rgba(255,255,255,.10); --text:#f7f8ff; --muted:#99a2bd; --violet:#8b6cff; --cyan:#53e7ff; --green:#4fe0a4; --orange:#ffb454; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background: radial-gradient(circle at 15% 5%, rgba(139,108,255,.18), transparent 30%), radial-gradient(circle at 90% 0%, rgba(83,231,255,.10), transparent 25%), var(--bg); }
.block-container { max-width:1300px; padding-top:2rem; padding-bottom:4rem; }
.hero { padding:34px 36px; border:1px solid var(--line); border-radius:28px; background:linear-gradient(135deg,rgba(20,26,50,.92),rgba(9,13,27,.84)); box-shadow:0 24px 80px rgba(0,0,0,.35); position:relative; overflow:hidden; }
.hero:after { content:''; position:absolute; width:360px; height:360px; right:-120px; top:-180px; border-radius:50%; border:1px solid rgba(83,231,255,.20); box-shadow:0 0 0 40px rgba(83,231,255,.03),0 0 0 80px rgba(83,231,255,.02); }
.eyebrow { color:var(--cyan); font-size:.78rem; letter-spacing:.16em; text-transform:uppercase; font-weight:700; }
.hero h1 { font-family:'Space Grotesk'; font-size:3.3rem; line-height:1.0; margin:.45rem 0 .8rem; letter-spacing:-.045em; }
.hero p { color:var(--muted); font-size:1.05rem; max-width:760px; }
.pill { display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,.04); color:#dfe4f5; font-size:.82rem; margin:5px 6px 0 0; }
.card { border:1px solid var(--line); border-radius:20px; padding:22px; background:linear-gradient(180deg,rgba(18,24,46,.86),rgba(11,16,31,.88)); }
.card h3 { font-family:'Space Grotesk'; margin-top:0; }
.trace { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.83rem; color:#d7dcf1; background:#070a14; border:1px solid var(--line); border-radius:14px; padding:15px; }
.source { border:1px solid var(--line); border-radius:15px; padding:14px 16px; margin:8px 0; background:rgba(255,255,255,.025); }
.source a { color:var(--cyan); text-decoration:none; }
.small { color:var(--muted); font-size:.86rem; }
.warning { border-left:3px solid var(--orange); background:rgba(255,180,84,.08); padding:13px 16px; border-radius:10px; }
.good { border-left:3px solid var(--green); background:rgba(79,224,164,.08); padding:13px 16px; border-radius:10px; }
.danger { border-left:3px solid #ff6678; background:rgba(255,102,120,.08); padding:13px 16px; border-radius:10px; }
.mechanic-card { border:1px solid var(--line); border-radius:18px; padding:18px; background:linear-gradient(180deg,rgba(16,22,42,.92),rgba(8,12,25,.94)); margin-bottom:12px; }
.mechanic-title { font-family:'Space Grotesk'; font-size:1.03rem; font-weight:700; color:#f7f8ff; }
.mechanic-meta { color:var(--muted); font-size:.83rem; margin-top:4px; }
.badge { display:inline-block; margin-top:9px; padding:5px 8px; border-radius:999px; border:1px solid var(--line); background:rgba(83,231,255,.06); color:#dffbff; font-size:.74rem; }
button[kind="primary"] { border-radius:14px !important; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0a0f1d 0%,#070914 100%); border-right:1px solid var(--line); }
label, .stMarkdown, .stText, .stCaption { color:#e9edfa; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "result" not in st.session_state:
    st.session_state.result = None
if "mechanics" not in st.session_state:
    st.session_state.mechanics = None
if "location" not in st.session_state:
    st.session_state.location = None

with st.sidebar:
    st.markdown("## 🚘 AutoSage AI")
    st.caption("Vehicle troubleshooting intelligence")
    st.divider()
    vehicle_type_label = st.radio("Vehicle", ["🏍️ Two-wheeler", "🚗 Four-wheeler"], index=1)
    vehicle_type = "two_wheeler" if "Two" in vehicle_type_label else "four_wheeler"
    make = st.text_input("Brand", placeholder="e.g. Hyundai")
    model = st.text_input("Model", placeholder="e.g. i20")
    year = st.text_input("Year", placeholder="e.g. 2022")
    fuel = st.selectbox("Fuel / power", ["Petrol", "Diesel", "CNG", "Electric", "Hybrid", "Unknown"])
    language_mode = st.selectbox(
        "Response language",
        ["Auto", "Hinglish", "English", "Hindi"],
        help="Auto mode detects common Hinglish/Roman-Hindi patterns.",
    )
    st.divider()
    provider = os.getenv("LLM_PROVIDER", "ollama").upper()
    st.markdown(f"**LLM:** `{provider}`")
    st.caption("Local: Ollama • Deploy: Hugging Face Inference")

st.markdown("""
<div class="hero">
  <div class="eyebrow">AI-powered vehicle intelligence</div>
  <h1>Know what's wrong.<br>Know what to do next.</h1>
  <p>AutoSage combines retrieval-grounded vehicle knowledge, deterministic safety tools and an LLM agent to turn everyday vehicle symptoms into a structured troubleshooting plan — and can connect you to nearby repair shops when professional inspection is recommended.</p>
  <div>
    <span class="pill">🏍️ 2-Wheeler</span><span class="pill">🚗 4-Wheeler</span><span class="pill">🧠 RAG</span><span class="pill">🛠️ Tools</span><span class="pill">🤖 Agent</span><span class="pill">📍 Nearby Mechanics</span>
  </div>
</div>
""", unsafe_allow_html=True)
st.write("")

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Diagnose", "📍 Nearby Mechanics", "🧠 System Trace", "📚 Research Base"])

with tab1:
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="card"><h3>Describe the symptom</h3><div class="small">Write it naturally. Add a dashboard code, warning light, sound, timing, or driving condition when you know it.</div></div>', unsafe_allow_html=True)
        st.write("")
        default_query = st.session_state.get("prefill", "")
        query = st.text_area(
            "",
            value=default_query,
            placeholder="Example: Meri 2022 petrol car mein P0420 aa raha hai, check-engine light on hai aur gaadi normally chal rahi hai. Kya check karna chahiye?",
            height=170,
            label_visibility="collapsed",
        )
        st.caption("💬 Hinglish is supported — e.g. *Meri bike start nahi ho rahi, self maarne pe click ki awaaz aa rahi hai. Kya check karu?*")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⚡ No-start", use_container_width=True):
                st.session_state.prefill = "Meri vehicle start nahi ho rahi. Self press karne pe clicking ki awaaz aa rahi hai."
                st.rerun()
        with c2:
            if st.button("🟠 Warning light", use_container_width=True):
                st.session_state.prefill = "Meri car mein check-engine light on hai aur P0420 aa raha hai. Iska kya matlab hai aur mujhe kya check karna chahiye?"
                st.rerun()
        with c3:
            if st.button("🔴 Brake issue", use_container_width=True):
                st.session_state.prefill = "Meri car ke brakes se grinding ki awaaz aa rahi hai aur braking pehle se weak lag rahi hai."
                st.rerun()
        st.write("")
        if st.button("🚀 RUN SMART DIAGNOSIS", type="primary", use_container_width=True):
            if not query.strip():
                st.warning("Describe the vehicle problem first.")
            elif not make.strip() or not model.strip():
                st.warning("Add at least the vehicle brand and model in the sidebar.")
            else:
                with st.spinner("Agent is planning → calling tools → retrieving evidence → synthesizing..."):
                    st.session_state.result = analyze(vehicle_type, make, model, year or "Unknown year", fuel, query.strip(), language_mode)
                    st.session_state.prefill = ""
                    st.session_state.mechanics = None
    with right:
        st.markdown("""
        <div class="card">
        <h3>Designed for real-world uncertainty</h3>
        <p class="small">AutoSage separates <b>evidence</b>, <b>tool outputs</b> and <b>LLM explanation</b>. It never treats a symptom as proof that a particular part is bad.</p>
        <div class="good"><b>Safety-first gate</b><br>Brake, steering, fuel-leak, severe overheating and other red-flag symptoms are escalated instead of receiving risky DIY advice.</div>
        <br>
        <div class="good"><b>Mechanic handoff</b><br>When a high-risk issue is detected, the user can explicitly share their location to find nearby repair shops.</div>
        <br>
        <div class="warning"><b>Privacy by design</b><br>AutoSage only uses location when the user chooses the location finder. The app itself does not save a location database.</div>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.result:
        result = st.session_state.result
        st.write("")
        st.markdown('<div class="card"><h3>Diagnostic guidance</h3></div>', unsafe_allow_html=True)
        st.markdown(result["answer"])

        if result.get("mechanic_recommended"):
            st.markdown("""
            <div class="danger"><b>Professional inspection recommended.</b><br>
            This result contains a higher-risk symptom. Open the <b>Nearby Mechanics</b> tab to share your location and find repair shops in the area.</div>
            """, unsafe_allow_html=True)

        with st.expander("🔧 Agent tool call — show me the evidence", expanded=True):
            st.markdown(f'<div class="trace">TOOL: {html.escape(str(result["tool"]))}<br>REASON: {html.escape(str(result["planner_reason"] or "Deterministic fallback"))}<br><br>RESULT:<br>{html.escape(str(result["tool_result"]))}</div>', unsafe_allow_html=True)

        st.caption(f"Detected input: {result.get('detected_language', 'unknown')} • Response: {result.get('response_language', 'Auto')}")
        st.markdown("### Retrieved research")
        for d in result["evidence"]:
            meta = d["metadata"]
            st.markdown(f'<div class="source"><b>{html.escape(str(meta.get("title","Source")))}</b><br><span class="small">{html.escape(str(meta.get("source_name","Unknown source")))}</span><br><a href="{html.escape(str(meta.get("source_url","#")))}" target="_blank">Open source</a></div>', unsafe_allow_html=True)

with tab2:
    st.markdown("""
    <div class="card">
    <h3>📍 Find a nearby mechanic</h3>
    <p class="small">Use your current device location for a map of nearby repair shops, or enter a city/area/pincode instead. Location sharing is optional.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown("### 1. Choose how to share your area")
        location_mode = st.radio("Location method", ["Use my device location", "Enter area / city / pincode"], label_visibility="collapsed")
        coords = None
        if location_mode == "Use my device location":
            st.info("Your browser will ask for location permission. AutoSage only uses the coordinates to search nearby repair shops for this session.")
            device_location = streamlit_geolocation()
            if isinstance(device_location, dict):
                direct_lat = device_location.get("latitude")
                direct_lon = device_location.get("longitude")
                nested = device_location.get("coords") or {}
                lat = direct_lat if direct_lat is not None else nested.get("latitude")
                lon = direct_lon if direct_lon is not None else nested.get("longitude")
                if lat is not None and lon is not None:
                    coords = {"latitude": float(lat), "longitude": float(lon), "label": "Your device location"}
                    st.session_state.location = coords
                elif device_location.get("error"):
                    st.warning("Location permission was not available. You can use the area/city option instead.")
            elif st.session_state.location:
                coords = st.session_state.location
        else:
            area = st.text_input("Area / city / pincode", placeholder="e.g. Ahmedabad 380015")
            if st.button("📍 Locate this area", use_container_width=True):
                if not area.strip():
                    st.warning("Enter an area, city or pincode first.")
                else:
                    # Respect Nominatim's public-service rate expectation and avoid repeated lookups.
                    last_call = st.session_state.get("last_geocode_call", 0.0)
                    wait = 1.1 - (time.time() - last_call)
                    if wait > 0:
                        time.sleep(wait)
                    with st.spinner("Finding the area on the map..."):
                        loc = geocode_location(area)
                    st.session_state.last_geocode_call = time.time()
                    if loc.get("ok"):
                        st.session_state.location = {
                            "latitude": loc["latitude"],
                            "longitude": loc["longitude"],
                            "label": loc.get("display_name", area),
                        }
                        st.success(f"Located: {loc.get('display_name', area)}")
                    else:
                        st.error(loc.get("error", "Could not locate that area."))
            coords = st.session_state.location

        radius_km = st.slider("Search radius", min_value=2, max_value=10, value=5, step=1, help="The public Overpass search is limited to a modest radius for responsiveness.")

        if coords:
            st.success(f"📍 {coords.get('label','Location ready')}: {coords['latitude']:.5f}, {coords['longitude']:.5f}")
            if st.button("🔧 FIND NEARBY MECHANICS", type="primary", use_container_width=True):
                with st.spinner("Searching nearby repair shops..."):
                    st.session_state.mechanics = find_nearby_mechanics(
                        coords["latitude"], coords["longitude"], vehicle_type, int(radius_km * 1000)
                    )
        else:
            st.caption("Share your location or enter an area to activate the mechanic finder.")

    with right:
        result = st.session_state.get("mechanics")
        if result and result.get("ok"):
            rows = result.get("mechanics", [])
            if rows:
                import pandas as pd
                map_rows = [{"lat": r["latitude"], "lon": r["longitude"], "name": r["name"]} for r in rows]
                st.map(pd.DataFrame(map_rows), latitude="lat", longitude="lon", zoom=13, height=330)
                st.caption(f"Showing {len(rows)} nearby repair listings • {result.get('attribution','© OpenStreetMap contributors')}")
            else:
                st.info("No repair listings were found in this radius. Try a larger radius or a more central location.")
        elif result and not result.get("ok"):
            st.error(result.get("error", "Nearby mechanic search failed."))
        else:
            st.markdown("""
            <div class="card">
            <h3>What the tool does</h3>
            <div class="trace">USER LOCATION<br>↓<br>find_nearby_mechanics()<br>↓<br>OpenStreetMap Overpass<br>↓<br>distance-sort repair shops<br>↓<br>map + directions links</div>
            </div>
            """, unsafe_allow_html=True)

    if st.session_state.get("mechanics", {}).get("ok"):
        rows = st.session_state["mechanics"].get("mechanics", [])
        st.markdown("### Nearby options")
        for idx, row in enumerate(rows, 1):
            maps_url = f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"
            website = row.get("website")
            phone = row.get("phone")
            extras = []
            if phone:
                extras.append(f"📞 {html.escape(str(phone))}")
            if website:
                extras.append(f"🌐 <a href=\"{html.escape(str(website))}\" target=\"_blank\">Website</a>")
            extra_html = " • ".join(extras)
            st.markdown(f"""
            <div class="mechanic-card">
              <div class="mechanic-title">{idx:02d} · {html.escape(str(row['name']))}</div>
              <div class="mechanic-meta">{row['distance_km']:.2f} km away • {html.escape(str(row['specialization']))}</div>
              <span class="badge">{html.escape(str(row['compatibility']))}</span>
              <div class="small" style="margin-top:10px">{html.escape(str(row['address']))}</div>
              <div class="small" style="margin-top:7px">{extra_html}</div>
              <div style="margin-top:12px"><a href="{maps_url}" target="_blank">Open directions in Maps →</a></div>
            </div>
            """, unsafe_allow_html=True)
        st.caption("Mechanic listings and locations come from OpenStreetMap data and may be incomplete or outdated. Confirm availability, hours and expertise before travelling.")

with tab3:
    st.markdown("""
    <div class="card">
      <h3>What actually happens after you press Diagnose?</h3>
      <div class="trace">
      01  USER INPUT<br>
      &nbsp;&nbsp;&nbsp;vehicle type + make/model/year + symptom<br><br>
      02  AGENT PLANNER<br>
      &nbsp;&nbsp;&nbsp;chooses a domain tool<br><br>
      03  TOOL EXECUTION<br>
      &nbsp;&nbsp;&nbsp;OBD lookup / safety gate / system triage / maintenance / parts plan<br><br>
      04  RAG RETRIEVAL<br>
      &nbsp;&nbsp;&nbsp;searches the curated vehicle knowledge corpus<br><br>
      05  LLM SYNTHESIS<br>
      &nbsp;&nbsp;&nbsp;turns evidence + tool result into a structured guide<br><br>
      06  HUMAN-IN-CONTROL HANDOFF<br>
      &nbsp;&nbsp;&nbsp;high-risk issue → optional location sharing → nearby mechanic search
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.markdown("### Deliberate domain design decision")
    st.info("**The safety gate and location handoff are explicit, not hidden inside generation.** The LLM explains symptoms, but high-risk findings trigger a deterministic Python safety check. Only after the user chooses to share location does the mechanic-search tool run. This keeps safety and privacy decisions testable and user-controlled.")

    st.markdown("### Hackathon architecture")
    st.markdown("""
    - **RAG:** answers are grounded in a curated source corpus.
    - **Agent:** chooses the appropriate domain tool.
    - **Tools:** deterministic code handles safety, OBD lookup, system triage and nearby-mechanic search.
    - **LLM:** used for interpretation and natural-language synthesis.
    - **Location privacy:** device coordinates are only requested on the mechanic-finder flow; the app does not maintain a location database.
    """)

with tab4:
    st.markdown("### Curated research sources")
    sources = [
        ("NHTSA Tire Safety", "https://www.nhtsa.gov/vehicle-safety/tires", "Tire pressure, tire safety, maintenance guidance."),
        ("Motorcycle Safety Foundation — T-CLOCS", "https://msf-usa.org/documents/library/t-clocs-pre-ride-inspection-checklist/", "Two-wheeler pre-ride checks: tires, brakes, controls, lights, fluids."),
        ("U.S. EPA — OBD resources", "https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100LW9G.TXT", "OBD concepts, emissions monitoring and diagnostic information."),
        ("Hyundai Owner's Manuals", "https://ownersmanual.hyundai.com/", "Manufacturer example for warning lights and safety-specific procedures."),
    ]
    for name, url, desc in sources:
        st.markdown(f'<div class="source"><b>{html.escape(name)}</b><br><span class="small">{html.escape(desc)}</span><br><a href="{html.escape(url)}" target="_blank">{html.escape(url)}</a></div>', unsafe_allow_html=True)

st.markdown("<div style='text-align:center;color:#707a97;margin-top:30px;font-size:.8rem'>AutoSage AI • hackathon prototype • evidence-guided vehicle troubleshooting • English + Hinglish + Hindi • optional nearby mechanic handoff</div>", unsafe_allow_html=True)
