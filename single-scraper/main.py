import os
import requests
from datetime import datetime
import pytz
import json
import logging
from google.cloud import storage
from PIL import Image
import imagehash
import io
import base64

BUCKET_NAME = 'nyc-webcam-capture'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def scrape_all_cameras(event, context):
    """
    Cloud Function that scrapes a list of cameras.
    """
    try:
        logger.info(f"Function started. Message ID: {context.event_id}")

        # Fetch all cameras
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        all_cameras = response.json()
        logger.info(f"Fetched {len(all_cameras)} cameras from API.")

        cameras_to_scrape = all_cameras #[:50]
        central_park_camera = {
            "name": "Central Park @ 72nd St Post 37",
            "id": "3f04a686-f97c-4187-8968-cb09265e08ff"
        }
        # Add Central Park camera if it's not already in the list
        if not any(c['id'] == central_park_camera['id'] for c in cameras_to_scrape):
            cameras_to_scrape.append(central_park_camera)
        logger.info(f"Will attempt to scrape {len(cameras_to_scrape)} cameras.")

        ny_tz = pytz.timezone('America/New_York')
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)

        for camera in cameras_to_scrape:
            camera_name = camera.get("name")
            camera_id = camera.get("id")
            logger.info(f"Attempting to scrape camera: {camera_name} ({camera_id})")
            try:
                url = f"https://webcams.nyctmc.org/api/cameras/{camera_id}/image"
                
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                now = datetime.now(ny_tz)
                timestamp = now.strftime('%Y%m%d_%H%M%S')
                
                safe_name = "".join(c if c.isalnum() else "_" for c in camera_name)
                
                filename = f"data/{safe_name}/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/{timestamp}_{camera_id}.jpg"
                
                img_byte_arr = io.BytesIO()
                img = Image.open(io.BytesIO(response.content))
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(img_byte_arr, format='JPEG', quality=85)
                logger.info(f"Successfully processed image for {camera_name} ({camera_id})")
                img_byte_arr = img_byte_arr.getvalue()

                blob = bucket.blob(filename)
                blob.upload_from_string(img_byte_arr, 'image/jpeg')
                
                logger.info(f"Successfully scraped and uploaded image for {camera_name} ({camera_id}) to gs://{BUCKET_NAME}/{filename}")

            except Exception as e:
                logger.error(f"Error processing camera {camera_name} ({camera_id}): {e}")
        
        logger.info("Overall scraping process complete.")
        return "Scraping complete.", 200

    except Exception as e:
        logger.error(f"Fatal error in scrape_all_cameras function: {e}")
        return "Error: " + str(e), 500
