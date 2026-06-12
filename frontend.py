import os
import re
import time
import streamlit as st
from datetime import datetime
from urllib.parse import quote_plus

from langchain_core.messages import HumanMessage
from main import app, checkpointer

from tools.weather_tool import get_weather, WEATHER_CODES
from tools.pdf_tool import generate_itinerary_pdf

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide"
)

# ----------------------------------------------------------------------
# STYLES
# ----------------------------------------------------------------------
st.markdown("""
<style>

.stApp{
    background: linear-gradient(180deg, #050B1A 0%, #0a1330 100%);
    color:white;
}

.main-title{
    font-size:48px;
    font-weight:800;
    text-align:center;
    background: linear-gradient(90deg, #4f9dff, #9b6dff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}

.subtitle{
    text-align:center;
    color:#b6c2d9;
    margin-bottom: 24px;
    font-size:16px;
}

.section-label{
    font-size:13px;
    font-weight:700;
    letter-spacing:1px;
    color:#7fa6ff;
    text-transform:uppercase;
    margin: 18px 0 8px 0;
}

.stButton>button{
    width:100%;
    border-radius:12px;
    font-weight:600;
    transition: all 0.2s ease-in-out;
}

.stButton>button:hover{
    transform: translateY(-1px);
}

div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input{
    border-radius:12px !important;
}

/* Primary CTA */
.cta-btn button{
    height:56px;
    border-radius:14px;
    font-size:18px;
    background:linear-gradient(90deg,#1f6feb,#7c5cff) !important;
    color:white !important;
    border:none !important;
    box-shadow: 0 4px 18px rgba(95,99,255,0.35);
}
.cta-btn button:hover{
    box-shadow: 0 6px 22px rgba(95,99,255,0.5);
}

/* Animated agent timeline */
.timeline{
    display:flex;
    flex-direction:column;
    gap:8px;
    margin:6px 0 10px 0;
}
.timeline-step{
    display:flex;
    align-items:center;
    gap:12px;
    padding:12px 18px;
    border-radius:12px;
    background:#0E1B35;
    border:1px solid #1f2e4d;
    transition: all 0.35s ease;
}
.timeline-step.active{
    border-color:#1f6feb;
    box-shadow:0 0 14px rgba(31,111,235,0.45);
    background:#102246;
}
.timeline-step.done{
    border-color:#27c281;
    background:#0f2520;
}
.timeline-icon{
    font-size:20px;
    width:28px;
    text-align:center;
}
.timeline-label{
    font-size:15px;
    font-weight:600;
    flex:1;
}
.timeline-status{
    font-size:12px;
    color:#9fb3d1;
    font-weight:600;
}
.timeline-step.done .timeline-status{
    color:#27c281;
}
.timeline-step.active .timeline-status{
    color:#4f9dff;
}
.spin {
    display:inline-block;
    animation: spin 1s linear infinite;
}
@keyframes spin {
    100% { transform: rotate(360deg); }
}

/* Booking links */
.booking-link{
    display:inline-block;
    background:#1f6feb;
    color:white !important;
    padding:9px 16px;
    border-radius:10px;
    text-decoration:none;
    margin:4px 8px 4px 0;
    font-size:13px;
    font-weight:600;
    transition: all 0.2s ease;
}
.booking-link:hover{
    background:#3b8bff;
    transform: translateY(-1px);
}

/* Budget */
.budget-row{
    display:flex;
    justify-content:space-between;
    padding:8px 0;
    border-bottom:1px solid #1f2e4d;
    font-size:15px;
}
.budget-row:last-child{
    border-bottom:none;
    font-weight:700;
    color:#4f9dff;
}

/* Weather */
.weather-card{
    background:#0E1B35;
    border-radius:12px;
    padding:14px 8px;
    text-align:center;
    border:1px solid #1f2e4d;
}
.weather-day{
    font-size:13px;
    font-weight:700;
    color:#b6c2d9;
}
.weather-icon{
    font-size:26px;
    margin:6px 0;
}
.weather-temp{
    font-size:14px;
    font-weight:600;
}
.weather-rain{
    font-size:12px;
    color:#7fa6ff;
}

/* Chat history bubbles */
.chat-bubble-user{
    background:#1f6feb;
    padding:8px 12px;
    border-radius:10px;
    margin:4px 0;
    font-size:13px;
}
.chat-bubble-ai{
    background:#0E1B35;
    padding:8px 12px;
    border-radius:10px;
    margin:4px 0;
    border:1px solid #2c4a7a;
    font-size:13px;
}

</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------

AGENT_STEPS = [
    {"key": "flight_agent", "label": "Flight Agent — searching flights", "icon": "🛫"},
    {"key": "hotel_agent", "label": "Hotel Agent — finding hotels", "icon": "🏨"},
    {"key": "itinerary_agent", "label": "Itinerary Agent — building your plan", "icon": "🗺️"},
    {"key": "final_agent", "label": "Final Agent — finalizing response", "icon": "✅"},
]


def render_timeline(placeholder, current_index, completed_indices):
    """Render the animated agent timeline into a placeholder.
    IMPORTANT: build the HTML string with NO leading whitespace per line,
    otherwise Streamlit/Markdown renders it as a literal code block."""
    rows = []
    for i, step in enumerate(AGENT_STEPS):
        if i in completed_indices:
            css_class = "timeline-step done"
            status = "Done"
            icon = "✅"
        elif i == current_index:
            css_class = "timeline-step active"
            status = "Running..."
            icon = "<span class='spin'>⚙️</span>"
        else:
            css_class = "timeline-step"
            status = "Pending"
            icon = step["icon"]

        rows.append(
            f"<div class='{css_class}'>"
            f"<div class='timeline-icon'>{icon}</div>"
            f"<div class='timeline-label'>{step['label']}</div>"
            f"<div class='timeline-status'>{status}</div>"
            f"</div>"
        )

    html = "<div class='timeline'>" + "".join(rows) + "</div>"
    placeholder.markdown(html, unsafe_allow_html=True)


def extract_city_from_query(query: str) -> str:
    """Lightweight heuristic to guess the destination city/country from the query."""
    patterns = [
        r"(?:to|in|for)\s+([A-Z][a-zA-Z\s]{2,20})(?:\s+(?:trip|for|under|including|with|on))",
        r"(?:to|in)\s+([A-Z][a-zA-Z]{2,20})",
    ]
    for p in patterns:
        m = re.search(p, query)
        if m:
            return m.group(1).strip()

    words = query.split()
    for w in words[1:]:
        clean = w.strip(",.!?")
        if clean.isalpha() and clean[0].isupper() and len(clean) > 2:
            return clean
    return ""


def get_destination_city(destination_input: str, query: str) -> str:
    """Prefer the explicit destination field; fall back to regex guess from the query."""
    if destination_input and destination_input.strip():
        return destination_input.strip()
    return extract_city_from_query(query)


def estimate_budget(query: str, flight_results: str, hotel_results: str):
    """Rough budget estimator based on heuristics + any numbers found in the query."""
    user_budget = None
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*lakh", query, re.IGNORECASE)
    if lakh_match:
        user_budget = float(lakh_match.group(1)) * 100000

    if user_budget is None:
        amt_match = re.search(r"[₹$€]\s?(\d{3,7})", query)
        if amt_match:
            user_budget = float(amt_match.group(1))

    days_match = re.search(r"(\d+)\s*-?\s*day", query, re.IGNORECASE)
    days = int(days_match.group(1)) if days_match else 5

    flight_est = 18000 * 1
    hotel_est = 3500 * days
    food_est = 1200 * days
    local_transport_est = 800 * days
    activities_est = 1500 * days
    misc_est = 0.1 * (flight_est + hotel_est + food_est + local_transport_est + activities_est)

    total_est = flight_est + hotel_est + food_est + local_transport_est + activities_est + misc_est

    return {
        "days": days,
        "flight": flight_est,
        "hotel": hotel_est,
        "food": food_est,
        "local_transport": local_transport_est,
        "activities": activities_est,
        "misc": misc_est,
        "total": total_est,
        "user_budget": user_budget,
    }


def get_booking_links(city: str):
    city_q = quote_plus(city) if city else ""
    return {
        "flights": [
            ("Google Flights", f"https://www.google.com/travel/flights?q=flights%20to%20{city_q}"),
            ("Skyscanner", f"https://www.skyscanner.com/transport/flights/{city_q}"),
        ],
        "hotels": [
            ("Booking.com", f"https://www.booking.com/searchresults.html?ss={city_q}"),
            ("Agoda", f"https://www.agoda.com/search?city={city_q}"),
            ("MakeMyTrip", f"https://www.makemytrip.com/hotels/{city_q}-hotels.html"),
        ]
    }


def load_chat_history(thread_id: str):
    """Load past conversation state from the Postgres checkpointer (LangGraph memory)."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = app.get_state(config)
        if state and state.values:
            return state.values.get("messages", [])
    except Exception as e:
        st.sidebar.warning(f"Could not load history: {e}")
    return []


# ----------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------
with st.sidebar:

    st.title("✈ AI Travel Planner")

    user_id = st.text_input(
        "User ID",
        value="aarohi_user",
        help="Used to remember your conversation history across sessions."
    )

    st.markdown("---")

    st.markdown("<div class='section-label'>Powered By</div>", unsafe_allow_html=True)
    pb1, pb2 = st.columns(2)
    with pb1:
        st.info("LangGraph")
        st.info("PostgreSQL")
        st.info("AviationStack")
    with pb2:
        st.info("Groq Llama 3.3")
        st.info("Tavily Search")
        st.info("Open-Meteo")

    st.markdown("---")

    st.markdown("<div class='section-label'>Agent Pipeline</div>", unsafe_allow_html=True)
    for step in AGENT_STEPS:
        st.markdown(f"✅ {step['label'].split(' — ')[0]}")

    st.markdown("---")

    st.markdown("<div class='section-label'>Chat History</div>", unsafe_allow_html=True)

    if st.button("🔄 Load History", use_container_width=True):
        history = load_chat_history(user_id)
        if history:
            for msg in history[-10:]:
                role_class = "chat-bubble-user" if msg.__class__.__name__ == "HumanMessage" else "chat-bubble-ai"
                role_label = "🧑 You" if msg.__class__.__name__ == "HumanMessage" else "🤖 AI"
                content = getattr(msg, "content", "")
                if content:
                    short = content[:160] + ("..." if len(content) > 160 else "")
                    st.markdown(
                        f"<div class='{role_class}'><b>{role_label}:</b> {short}</div>",
                        unsafe_allow_html=True
                    )
        else:
            st.caption("No history found for this user yet.")


# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------
st.markdown("<div class='main-title'>✈ AI Travel Booking System</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle'>Four specialized AI agents work together to search flights, "
    "find hotels, create itineraries and plan your journey end-to-end.</div>",
    unsafe_allow_html=True
)

# ----------------------------------------------------------------------
# QUICK PROMPTS
# ----------------------------------------------------------------------
st.markdown("<div class='section-label'>Quick Start</div>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
quick_query = None

with col1:
    if st.button("🇯🇵 7 Days Japan", use_container_width=True):
        quick_query = "Plan a 7 day Japan trip under ₹2 lakh including flights, hotels and sightseeing."

with col2:
    if st.button("🇫🇷 Paris Trip", use_container_width=True):
        quick_query = "Plan a 5 day Paris trip under ₹1.5 lakh including flights, hotels and sightseeing."

with col3:
    if st.button("🇦🇪 Dubai Weekend", use_container_width=True):
        quick_query = "Plan a 3 day Dubai weekend trip under ₹80000 including flights and hotels."

with col4:
    if st.button("🏝 Bali Backpacking", use_container_width=True):
        quick_query = "Plan a 6 day Bali backpacking trip under ₹60000 including flights and hostels."


if "query_text" not in st.session_state:
    st.session_state.query_text = ""

if quick_query:
    st.session_state.query_text = quick_query

# ----------------------------------------------------------------------
# TRIP INPUT FORM
# ----------------------------------------------------------------------
st.markdown("<div class='section-label'>Plan Your Trip</div>", unsafe_allow_html=True)

query = st.text_area(
    "Describe your trip",
    height=140,
    placeholder="Example: Plan a 7 day Japan trip under ₹2 lakh including flights, hotels and sightseeing.",
    value=st.session_state.query_text,
    key="query_input"
)

dest_col, btn_col = st.columns([2, 1])

with dest_col:
    destination = st.text_input(
        "📍 Destination city (for Map & Weather)",
        placeholder="e.g. Tokyo, Paris, Dubai, Bali",
        key="destination_input"
    )

with btn_col:
    st.write("")
    st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
    generate = st.button("🚀 Generate My Travel Plan", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# AGENT EXECUTION (runs only when the button is clicked)
# Its only job is to run the graph and SAVE the result into session_state.
# ----------------------------------------------------------------------
if generate and query:

    st.markdown("<div class='section-label'>🧠 Agent Execution Timeline</div>", unsafe_allow_html=True)
    timeline_placeholder = st.empty()
    render_timeline(timeline_placeholder, current_index=-1, completed_indices=set())

    config = {
        "configurable": {
            "thread_id": user_id
        }
    }

    initial_state = {
        "messages": [
            HumanMessage(content=query)
        ],
        "user_query": query,
        "flight_results": "",
        "hotel_results": "",
        "itinerary": "",
        "llm_calls": 0
    }

    result = None
    completed = set()

    try:
        for step_output in app.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_state in step_output.items():
                for i, step in enumerate(AGENT_STEPS):
                    if step["key"] == node_name:
                        render_timeline(timeline_placeholder, current_index=i, completed_indices=completed)
                        time.sleep(0.4)
                        completed.add(i)
                        render_timeline(timeline_placeholder, current_index=-1, completed_indices=completed)

        final_state = app.get_state(config)
        result = final_state.values

    except Exception as e:
        st.error(f"Agent execution failed: {e}")
        result = None

    if result:
        render_timeline(timeline_placeholder, current_index=-1, completed_indices={0, 1, 2, 3})

        # Persist everything needed for display so it survives reruns
        # (tab clicks, map interactions, hovering widgets, etc.)
        st.session_state["last_result"] = {
            "query": query,
            "destination": destination,
            "final_response": result["messages"][-1].content,
            "flight_results": result.get("flight_results", ""),
            "hotel_results": result.get("hotel_results", ""),
            "itinerary_text": result.get("itinerary", ""),
            "llm_calls": result.get("llm_calls", 0),
            "generated_at": datetime.now().strftime("%H:%M"),
        }


# ----------------------------------------------------------------------
# RESULTS DISPLAY (runs on EVERY rerun as long as a result is saved)
# This block is OUTSIDE the "if generate" check, so switching tabs,
# interacting with the map, etc. will NOT make the results disappear.
# ----------------------------------------------------------------------
if "last_result" in st.session_state:

    data = st.session_state["last_result"]

    final_response = data["final_response"]
    flight_results = data["flight_results"]
    hotel_results = data["hotel_results"]
    itinerary_text = data["itinerary_text"]
    saved_query = data["query"]
    saved_destination = data["destination"]

    city_guess = get_destination_city(saved_destination, saved_query)

    st.write("")
    st.success("✅ Travel Plan Generated Successfully")

    # ----------------------------------------------------------------
    # METRICS ROW
    # ----------------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("LLM Calls", data.get("llm_calls", 0))
    with m2:
        st.metric("Generated At", data.get("generated_at", "—"))
    with m3:
        st.metric("Status", "Success ✅")
    with m4:
        st.metric("Destination", city_guess if city_guess else "—")

    st.write("")

    # ----------------------------------------------------------------
    # TABS
    # ----------------------------------------------------------------
    tab_final, tab_flights, tab_hotels, tab_itinerary, tab_map, tab_weather, tab_budget = st.tabs(
        ["📋 Final Plan", "🛫 Flights", "🏨 Hotels", "🗺️ Itinerary", "📍 Map", "☁️ Weather", "💰 Budget"]
    )

    # ---- Final Plan ----
    with tab_final:
        with st.container(border=True):
            st.markdown(final_response)

    # ---- Flights ----
    with tab_flights:
        with st.container(border=True):
            if flight_results.strip():
                st.markdown("**Flight Search Results**")
                st.text(flight_results)
            else:
                st.info("No flight results returned.")

        st.markdown("##### 🔗 Book Flights")
        links = get_booking_links(city_guess)
        link_html = "".join(
            f"<a class='booking-link' href='{url}' target='_blank'>{name} ↗</a>"
            for name, url in links["flights"]
        )
        st.markdown(link_html, unsafe_allow_html=True)

    # ---- Hotels ----
    with tab_hotels:
        with st.container(border=True):
            if hotel_results.strip():
                st.markdown("**Hotel Search Results**")
                st.markdown(hotel_results)
            else:
                st.info("No hotel results returned.")

        st.markdown("##### 🔗 Book Hotels")
        links = get_booking_links(city_guess)
        link_html = "".join(
            f"<a class='booking-link' href='{url}' target='_blank'>{name} ↗</a>"
            for name, url in links["hotels"]
        )
        st.markdown(link_html, unsafe_allow_html=True)

    # ---- Itinerary ----
    with tab_itinerary:
        with st.container(border=True):
            if itinerary_text.strip():
                st.markdown(itinerary_text)
            else:
                st.info("No itinerary generated.")

    # ---- Map ----
    with tab_map:
        if not FOLIUM_AVAILABLE:
            st.warning("Install `folium` and `streamlit-folium` to enable the map: `pip install folium streamlit-folium`")
        elif not city_guess:
            st.info("Enter a destination city above to see it on the map.")
        else:
            weather_data = get_weather(city_guess)
            if weather_data:
                lat, lon = weather_data["lat"], weather_data["lon"]
                m = folium.Map(location=[lat, lon], zoom_start=11, tiles="CartoDB dark_matter")
                folium.Marker(
                    [lat, lon],
                    popup=f"{weather_data['city']}, {weather_data['country']}",
                    tooltip=city_guess,
                    icon=folium.Icon(color="blue", icon="plane")
                ).add_to(m)
                st_folium(m, width=None, height=450, key="travel_map")
            else:
                st.info(f"Couldn't find map coordinates for '{city_guess}'.")

    # ---- Weather ----
    with tab_weather:
        if not city_guess:
            st.info("Enter a destination city above to see the weather forecast.")
        else:
            weather_data = get_weather(city_guess)
            if not weather_data:
                st.info(f"No weather data available for '{city_guess}'.")
            else:
                st.markdown(f"##### 7-Day Forecast — {weather_data['city']}, {weather_data['country']}")
                daily = weather_data["daily"]
                dates = daily.get("time", [])
                tmax = daily.get("temperature_2m_max", [])
                tmin = daily.get("temperature_2m_min", [])
                codes = daily.get("weathercode", [])
                rain = daily.get("precipitation_probability_max", [])

                cols = st.columns(len(dates)) if dates else []
                for i, col in enumerate(cols):
                    with col:
                        icon = WEATHER_CODES.get(codes[i], "🌤")
                        card_html = (
                            f"<div class='weather-card'>"
                            f"<div class='weather-day'>{dates[i][5:]}</div>"
                            f"<div class='weather-icon'>{icon}</div>"
                            f"<div class='weather-temp'>{tmax[i]:.0f}° / {tmin[i]:.0f}°</div>"
                            f"<div class='weather-rain'>💧 {rain[i]}%</div>"
                            f"</div>"
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

    # ---- Budget ----
    with tab_budget:
        budget = estimate_budget(saved_query, flight_results, hotel_results)

        b1, b2, b3 = st.columns(3)
        with b1:
            st.metric("Trip Duration", f"{budget['days']} days")
        with b2:
            st.metric("Estimated Total", f"₹{budget['total']:,.0f}")
        with b3:
            if budget["user_budget"]:
                diff = budget["user_budget"] - budget["total"]
                st.metric(
                    "Your Budget vs Estimate",
                    f"₹{budget['user_budget']:,.0f}",
                    delta=f"₹{diff:,.0f}"
                )
            else:
                st.metric("Your Stated Budget", "Not specified")

        st.markdown("##### Breakdown")
        with st.container(border=True):
            breakdown_rows = []
            for label, key in [
                ("✈️ Flights", "flight"),
                ("🏨 Hotels", "hotel"),
                ("🍽️ Food", "food"),
                ("🚕 Local Transport", "local_transport"),
                ("🎟️ Activities", "activities"),
                ("➕ Misc / Buffer (10%)", "misc"),
            ]:
                breakdown_rows.append(
                    f"<div class='budget-row'><span>{label}</span><span>₹{budget[key]:,.0f}</span></div>"
                )
            breakdown_rows.append(
                f"<div class='budget-row'><span>Total</span><span>₹{budget['total']:,.0f}</span></div>"
            )
            st.markdown("".join(breakdown_rows), unsafe_allow_html=True)

        st.caption("⚠️ This is a rough heuristic estimate, not a real-time quote.")

    # ----------------------------------------------------------------
    # PDF DOWNLOAD
    # ----------------------------------------------------------------
    st.write("")
    try:
        pdf_bytes = generate_itinerary_pdf(
            query=saved_query,
            final_response=final_response,
            flight_results=flight_results,
            hotel_results=hotel_results
        )
        st.download_button(
            label="📄 Download Itinerary as PDF",
            data=pdf_bytes,
            file_name=f"travel_itinerary_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.warning(f"PDF generation unavailable: {e} (try `pip install fpdf2`)")