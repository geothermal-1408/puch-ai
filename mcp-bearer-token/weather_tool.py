# import os
# import requests
# from typing import Annotated
# from pydantic import Field, BaseModel
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # --- Rich Tool Description model (can be shared from a common models file later) ---
# class RichToolDescription(BaseModel):
#     description: str
#     use_when: str
#     side_effects: str | None = None

# # --- API Key for this specific tool ---
# OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

# # --- Tool Description (to be exported) ---
# WeatherToolDescription = RichToolDescription(
#     description="Fetches the current weather for a specified city.",
#     use_when="User asks about the weather, temperature, or climate in a particular location.",
#     side_effects="Makes a real-time request to an external weather API."
# )

# # --- Tool Function (to be exported) ---
# async def get_weather(
#     city: Annotated[str, Field(description="The city name to get the weather for, e.g., 'Kolkata' or 'London'")]
# ) -> str:
#     """
#     Fetches the current weather from the OpenWeatherMap API for a given city.
#     """
#     if not OPENWEATHER_API_KEY:
#         return "Error: OpenWeatherMap API key is not configured."

#     base_url = "http://api.openweathermap.org/data/2.5/weather"
#     params = {
#         "q": city,
#         "appid": OPENWEATHER_API_KEY,
#         "units": "metric"  # For Celsius
#     }
    
#     try:
#         response = requests.get(base_url, params=params)
#         response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
#         data = response.json()
        
#         if data.get("cod") != 200:
#             return f"Error: Could not retrieve weather for {city}. Reason: {data.get('message', 'Unknown error')}"

#         main = data['main']
#         weather_desc = data['weather'][0]['description']
#         temp = main['temp']
#         feels_like = main['feels_like']
#         humidity = main['humidity']

#         return (
#             f"☀️ Weather in {data['name']}:\n"
#             f"- Condition: {weather_desc.title()}\n"
#             f"- Temperature: {temp}°C\n"
#             f"- Feels Like: {feels_like}°C\n"
#             f"- Humidity: {humidity}%"
#         )

#     except requests.exceptions.HTTPError as http_err:
#         if response.status_code == 404:
#             return f"Error: The city '{city}' could not be found. Please check the spelling."
#         return f"Error: An HTTP error occurred: {http_err}"
#     except Exception as e:
#         return f"An unexpected error occurred: {str(e)}"