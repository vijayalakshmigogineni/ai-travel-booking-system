import requests

def get_weather(city: str):
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1}
        ).json()

        if not geo.get("results"):
            return None

        loc = geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]

        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                "timezone": "auto",
                "forecast_days": 7
            }
        ).json()

        return {
            "city": loc.get("name"),
            "country": loc.get("country"),
            "lat": lat,
            "lon": lon,
            "daily": weather.get("daily", {})
        }
    except Exception:
        return None


WEATHER_CODES = {
    0: "☀️ Clear", 1: "🌤 Mostly Clear", 2: "⛅ Partly Cloudy", 3: "☁️ Overcast",
    45: "🌫 Fog", 48: "🌫 Fog", 51: "🌦 Light Drizzle", 61: "🌧 Light Rain",
    63: "🌧 Rain", 65: "🌧 Heavy Rain", 71: "❄️ Snow", 80: "🌧 Rain Showers",
    95: "⛈ Thunderstorm"
}