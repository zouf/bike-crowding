from flask import Flask, render_template
import requests
import os
import json
from google.cloud import storage
from pprint import pprint

# Initialize Flask app
app = Flask(__name__)

# Constants
CAMERA_API_URL = "https://webcams.nyctmc.org/api/cameras"
GCS_BUCKET_NAME = "bike-crowding"
GCS_FILE_PATH = "metadata/latest_status.json"

def fetch_camera_data():
    """Fetch camera data from the API."""
    try:
        response = requests.get(CAMERA_API_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error fetching camera data: {e}")
        return []

def get_camera_info():
    """Fetch and parse JSON data from Google Cloud Storage."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_FILE_PATH)
        json_content = blob.download_as_text()
        return json.loads(json_content)
    except Exception as e:
        app.logger.error(f"Error fetching GCS file: {e}")
        return {}

@app.route('/')
def index():
    """Render the Google Maps page with camera markers."""
    # Fetch camera data from API and GCS
    cameras = fetch_camera_data()
    camera_info = get_camera_info()

    # Build a dictionary for camera name to GCS file link mapping
    name_to_link = {
        cam['camera_name']: f'https://storage.cloud.google.com/bike-crowding/{cam["filename"]}'
        for cam in camera_info.get('details', [])
    }

    # Filter and structure the camera data for rendering
    camera_data = [
        {
            'name': camera['name'],
            'gcslink': name_to_link.get(camera["name"], 'UNKNOWN'),
            'latitude': camera['latitude'],
            'longitude': camera['longitude'],
            'imageUrl': camera['imageUrl'],
            'cameraUrl': f"https://webcams.nyctmc.org/api/cameras/{camera['id']}"
        }
        for camera in cameras if camera.get('isOnline') == 'true'
    ]

    return render_template('map.html', cameras=camera_data, API_KEY=os.environ['GOOGLE_MAPS_API_KEY'])

if __name__ == '__main__':
    app.run(debug=True)
