# ✈️ AI Travel Booking System

A multi-agent AI travel planning system built using LangGraph, Groq Llama 3.3, PostgreSQL Memory, Tavily Search, AviationStack, Weather APIs and Streamlit.

---

## Features

### Flight Agent
- Searches flights using AviationStack API
- Retrieves airline, departure, arrival and status

### Hotel Agent
- Searches hotels using Tavily Search
- Finds relevant accommodation options

### Itinerary Agent
- Generates detailed travel itinerary
- Uses Groq Llama 3.3 70B

### Final Agent
- Produces final travel recommendations

### Memory
- PostgreSQL checkpointing
- Remembers previous conversations

### Weather Forecast
- 7-day destination weather
- Open Meteo API

### Maps
- Interactive destination maps
- Folium integration

### Budget Estimator
- Travel cost estimation
- Flights, hotels, food and activities

### PDF Export
- Download itinerary as PDF

---

## Architecture

User Query
↓
Flight Agent
↓
Hotel Agent
↓
Itinerary Agent
↓
Final Agent
↓
Response

Memory Layer:
PostgreSQL + LangGraph Checkpointer

---

## Technologies

- LangGraph
- LangChain
- Groq
- PostgreSQL
- Streamlit
- Tavily Search
- AviationStack
- Open Meteo
- Folium
- FPDF

---

## Installation

### Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-travel-booking-system.git

cd ai-travel-booking-system
```

### Create Virtual Environment

```bash
python -m venv langgraph-venv

source langgraph-venv/bin/activate
```

Windows:

```bash
langgraph-venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create:

```env
.env
```

Add:

```env
GROQ_API_KEY=xxx

TAVILY_API_KEY=xxx

AVIATIONSTACK_API_KEY=xxx

DATABASE_URL=postgresql://username:password@localhost:5432/database
```

### Run

```bash
streamlit run frontend.py
```

---

## Screenshots

(Add screenshots here)

---

## Future Enhancements

- Flight booking integration
- Hotel booking integration
- Real-time pricing
- Visa assistant
- Travel document generation
- Multi-language support
- AI budget optimizer

---

## Author

Vijayalakshmi
Computer Science Student