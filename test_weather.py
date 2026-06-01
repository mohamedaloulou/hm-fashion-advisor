import requests

API_KEY = "your_api_key_here"
CITY = "London"

# Step 1: Geocoding API — convert city name to lat/lon
geo_url = "http://api.openweathermap.org/geo/1.0/direct"
geo_params = {"q": CITY, "limit": 1, "appid": API_KEY}

print(f"Testing OpenWeatherMap API for city: {CITY}\n")

try:
    geo_resp = requests.get(geo_url, params=geo_params, timeout=8)

    if geo_resp.status_code == 401:
        print("❌ API key is INVALID or NOT YET ACTIVE (401 Unauthorized)")
        print("   → Wait up to 2 hours after creating the key, then try again.")
        exit()

    geo_data = geo_resp.json()
    if not geo_data:
        print(f"❌ City '{CITY}' not found. Try a different city name.")
        exit()

    lat = geo_data[0]["lat"]
    lon = geo_data[0]["lon"]
    print(f"📍 Geocoded '{CITY}' → lat={lat}, lon={lon}\n")

    # Step 2: Weather API — get current weather using lat/lon
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    weather_params = {"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}

    weather_resp = requests.get(weather_url, params=weather_params, timeout=8)

    if weather_resp.status_code == 200:
        data = weather_resp.json()
        print("✅ API key is WORKING!\n")
        print(f"📍 Location:     {data['name']}, {data['sys']['country']}")
        print(f"🌡️  Temperature:  {data['main']['temp']}°C (feels like {data['main']['feels_like']}°C)")
        print(f"🌤️  Conditions:   {data['weather'][0]['description'].capitalize()}")
        print(f"💧 Humidity:     {data['main']['humidity']}%")
        print(f"💨 Wind:         {round(data['wind']['speed'] * 3.6, 1)} km/h")
        print(f"☁️  Cloudiness:   {data['clouds']['all']}%")
        print(f"👁️  Visibility:   {data.get('visibility', 'N/A')} m")
        print(f"🔽 Pressure:     {data['main']['pressure']} hPa")
        if "rain" in data:
            print(f"🌧️  Rain (1h):    {data['rain'].get('1h', 0)} mm")
        if "snow" in data:
            print(f"❄️  Snow (1h):    {data['snow'].get('1h', 0)} mm")
    else:
        print(f"❌ Weather API error: {weather_resp.status_code}")
        print(weather_resp.text)

except requests.exceptions.ConnectionError:
    print("❌ No internet connection.")
except requests.exceptions.Timeout:
    print("❌ Request timed out.")
except Exception as e:
    print(f"❌ Error: {e}")
