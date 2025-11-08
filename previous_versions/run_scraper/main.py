import requests
from datetime import datetime
import pytz
import json
import time
import logging
import os
from pathlib import Path
from flask import Flask
from PIL import Image
import imagehash
import io

app = Flask(__name__)

BUCKET_NAME = 'nyc-webcam-capture'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraScraper:
    def __init__(self):
        self.ny_tz = pytz.timezone('America/New_York')
        from google.cloud import storage
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(BUCKET_NAME)

    def get_camera_by_name(self, camera_name):
        try:
            url = "https://webcams.nyctmc.org/api/cameras"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            all_cameras = response.json()
            for camera in all_cameras:
                if camera['name'] == camera_name:
                    return camera
        except requests.RequestException as e:
            logger.error(f"Failed to fetch camera list: {e}")
            return None
        return None

    def download_camera_image(self, camera):
        try:
            camera_id = camera['id']
            url = f"https://webcams.nyctmc.org/api/cameras/{camera_id}/image"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            now = datetime.now(self.ny_tz)
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            
            safe_name = "".join(c if c.isalnum() else "_" for c in camera['name'])
            
            filename = f"data/{safe_name}/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/{timestamp}_{camera_id}.jpg"
            
            img_byte_arr = io.BytesIO()
            img = Image.open(io.BytesIO(response.content))
            img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()

            blob = self.bucket.blob(filename)
            blob.upload_from_string(img_byte_arr, 'image/jpeg')
            logger.info(f"Uploaded to GCS: gs://{BUCKET_NAME}/{filename}")
            
            return {"status": "success", "filename": filename}
            
        except Exception as e:
            logger.error(f"Error processing camera {camera.get('id', 'unknown')}: {e}")
            return {"status": "error", "error": str(e)}

@app.route('/')
def scrape():
    scraper = CameraScraper()
    camera = scraper.get_camera_by_name('Central Park @ 72nd St Post 37')
    if not camera:
        return "Camera not found", 404

    results = []
    for i in range(3):
        logger.info(f"Scraping attempt {i+1}...")
        result = scraper.download_camera_image(camera)
        results.append(result)
        time.sleep(5) # Wait 5 seconds between scrapes

    return json.dumps(results, indent=2)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
