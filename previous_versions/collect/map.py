import requests
import json
import os

# Step 1: Fetch the camera data from the API
url = "https://webcams.nyctmc.org/api/cameras"
response = requests.get(url)
data = response.json()  # Assuming the API returns a JSON response

# Step 2: Generate the HTML for the Google Map
API_KEY = os.environ['GOOGLE_MAPS_API_KEY']
html_content = """
<!DOCTYPE html>
<html>
  <head>
    <title>Camera Locations</title>
<script src="https://maps.googleapis.com/maps/api/js?key={{ API_KEY }}&callback=initMap" async defer></script>
    <style>
      #map {
        height: 100%;
        width: 100%;
      }
      html, body {
        height: 100%;
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <script>
      let map;

      function initMap() {
        map = new google.maps.Map(document.getElementById("map"), {
          center: { lat: 40.730610, lng: -73.935242 },  // Default center (NYC)
          zoom: 11,
        });
"""

# Step 3: Add markers for each camera
for camera in data:
    name = camera['name']
    latitude = camera['latitude']
    longitude = camera['longitude']
    image_url = camera['imageUrl']
    camera_url = f"https://webcams.nyctmc.org/api/cameras/{camera['id']}"

    # Corrected way of adding f-string inside JavaScript code
    html_content += f"""
        const marker = new google.maps.Marker({{
          position: {{ lat: {latitude}, lng: {longitude} }},
          map: map,
          title: "{name}",
        }});

        const infoWindow = new google.maps.InfoWindow({{
          content: `
            <div>
              <h3>{name}</h3>
              <a href="{camera_url}" target="_blank">
                <img src="{image_url}" alt="{name}" style="width: 100px; height: auto;">
              </a>
              <p><a href="{camera_url}" target="_blank">View Camera</a></p>
            </div>
          `,
        }});

        marker.addListener("click", () => {{
          infoWindow.open(map, marker);
        }});
    """

# Step 4: Close the HTML content and the JavaScript
html_content += """
      }
    </script>
  </body>
</html>
"""

# Step 5: Write the HTML content to a file
with open("camera_map.html", "w") as file:
    file.write(html_content)

print("HTML file 'camera_map.html' has been generated!")
