from flask import Flask, render_template
import requests
import os

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

@app.route('/')
def index():
    """Render the Google Maps page with camera markers"""
    # Fetch the camera data
    cameras = fetch_camera_data()

    # Prepare the camera data to pass into the template
    camera_data = [
        {
            'name': camera['name'],
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


