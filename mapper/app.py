from flask import Flask, render_template
import requests
from pprint import pprint
import os
from google.cloud import storage
import functools
import json
app = Flask(__name__)

# Step 1: Fetch camera data from the API
CAMERA_API_URL = "https://webcams.nyctmc.org/api/cameras"

def fetch_camera_data():
    """Fetch the camera data from the API"""
    response = requests.get(CAMERA_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        return []



def get_camera_info():
    """Read and parse a JSON file from Google Cloud Storage."""
    storage_client = storage.Client()

    # Define bucket and file path
    bucket_name = "bike-crowding"
    file_path = "metadata/latest_status.json"

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
 
    # Download the JSON content as a string
    json_content = blob.download_as_text()
    # Parse the JSON string
    return json.loads(json_content)



@app.route('/')
def index():
    """Render the Google Maps page with camera markers"""
    # Fetch the camera data
    cameras = fetch_camera_data()
    name2link = {}
    for cam in get_camera_info()['details']:
        name2link[cam['camera_name']] = f'https://storage.cloud.google.com/bike-crowding/{cam["filename"]}'


    camera_data = [
        {
            'name': camera['name'],
            'gcslink': name2link.get(camera["name"], 'UNKNOWN'),
            'latitude': camera['latitude'],
            'longitude': camera['longitude'],
            'imageUrl': camera['imageUrl'],
            'cameraUrl': f"https://webcams.nyctmc.org/api/cameras/{camera['id']}"
        }
        for camera in cameras if camera.get('isOnline') == 'true'
    ]
    
    return render_template('map.html', cameras=camera_data, API_KEY=os.environ['GOOGLE_MAPS_API_KEY'])

if __name__ == '__main__':
    pprint(get_camera_info())
    app.run(debug=True)

