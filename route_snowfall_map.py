import googlemaps
import requests
import folium
from datetime import datetime, timedelta

# 1. Function to fetch route data from Google Maps Directions API
def fetch_route_data(api_key, origin, destination, waypoints, departure_time, stop_durations):
    """
    Fetch route details from Google Maps Directions API with stops.
    Returns a list of waypoints with lat/lon and timestamps.
    """
    gmaps = googlemaps.Client(key=api_key)

    directions_result = gmaps.directions(
        origin,
        destination,
        mode="driving",
        waypoints=waypoints,  # List of intermediate stops
        departure_time=departure_time
    )

    if not directions_result:
        print("No directions found.")
        return []

    route = directions_result[0]
    waypoints_data = []
    timestamp = departure_time

    for i, step in enumerate(route["legs"]):
        for substep in step["steps"]:
            location = substep["start_location"]
            duration = substep["duration"]["value"]  # Duration in seconds
            waypoints_data.append({
                "lat": location["lat"],
                "lon": location["lng"],
                "time": timestamp
            })
            timestamp += timedelta(seconds=duration)

        # Add the endpoint of this leg
        end_location = step["end_location"]
        waypoints_data.append({
            "lat": end_location["lat"],
            "lon": end_location["lng"],
            "time": timestamp
        })

        # Add stop duration at each waypoint (if specified)
        if i < len(stop_durations):
            timestamp += timedelta(minutes=stop_durations[i])

    return waypoints_data

# 2. Function to fetch snowfall data from a weather API
def fetch_snowfall_data(api_key, waypoints):
    """
    Fetch snowfall predictions for waypoints along the route.
    """
    url = "http://api.weatherapi.com/v1/forecast.json"
    snowfall_data = []

    for point in waypoints:
        params = {
            "key": api_key,
            "q": f"{point['lat']},{point['lon']}",
            "dt": point["time"].strftime("%Y-%m-%d")
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Extract snowfall and match it with the hour
        forecast_day = data.get("forecast", {}).get("forecastday", [])[0]
        hour_data = next(
            (hour for hour in forecast_day["hour"] if hour["time"] == point["time"].strftime("%Y-%m-%d %H:%M")),
            None
        )

        snowfall = hour_data.get("snow", 0.0) if hour_data else 0.0
        snowfall_data.append({
            "lat": point["lat"],
            "lon": point["lon"],
            "time": point["time"],
            "snowfall": snowfall
        })

    return snowfall_data

# 3. Function to create a map
def create_snowfall_map(snowfall_data, output_file="snowfall_map.html"):
    """
    Visualize snowfall predictions on a map using Folium.
    """
    if not snowfall_data:
        print("No snowfall data to display.")
        return

    # Create a map centered on the first data point
    m = folium.Map(location=[snowfall_data[0]["lat"], snowfall_data[0]["lon"]], zoom_start=10)

    for data in snowfall_data:
        color = "blue" if data["snowfall"] == 0 else "lightblue" if data["snowfall"] <= 2 else "darkblue"
        folium.CircleMarker(
            location=[data["lat"], data["lon"]],
            radius=5 + data["snowfall"] * 2,  # Adjust size for visibility
            popup=f"Time: {data['time']}<br>Snowfall: {data['snowfall']} cm",
            color=color,
            fill=True,
            fill_opacity=0.7
        ).add_to(m)

    m.save(output_file)
    print(f"Map saved to {output_file}")

# 4. Main script
if __name__ == "__main__":
    # API keys
    google_api_key = "your_google_maps_api_key"
    weather_api_key = "your_weather_api_key"

    # User inputs
    origin = input("Enter your starting location: ")
    destination = input("Enter your destination: ")
    waypoints_input = input("Enter stops along the way (comma-separated): ")
    waypoints = waypoints_input.split(",") if waypoints_input.strip() else []
    stop_durations_input = input("Enter stop durations in minutes for each stop (comma-separated): ")
    stop_durations = [int(d) for d in stop_durations_input.split(",")] if stop_durations_input.strip() else []
    departure_time = input("Enter departure time (YYYY-MM-DD HH:MM): ")
    departure_time = datetime.strptime(departure_time, "%Y-%m-%d %H:%M")

    # Fetch route data with stops
    route_with_stops = fetch_route_data(google_api_key, origin, destination, waypoints, departure_time, stop_durations)

    # Fetch snowfall data
    snowfall_data = fetch_snowfall_data(weather_api_key, route_with_stops)

    # Create a snowfall map
    create_snowfall_map(snowfall_data)
