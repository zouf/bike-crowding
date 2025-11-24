import os
import requests
from datetime import datetime, timedelta
import pytz
import json
import logging
from google.cloud import storage
from PIL import Image
import imagehash
import io
import base64
import concurrent.futures
import time
import warnings

# Suppress the specific Google Cloud SDK warning
warnings.filterwarnings("ignore", "Your application has authenticated using end user credentials from Google Cloud SDK")

BUCKET_NAME = 'nyc-webcam-capture'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def download_and_process_camera(camera, bucket):
    """
    Downloads and processes a single camera image with retry logic.
    """
    camera_name = camera.get("name")
    camera_id = camera.get("id")
    logger.info(f"Attempting to scrape camera: {camera_name} ({camera_id})")
    
    retries = 3
    for i in range(retries):
        try:
            url = f"https://webcams.nyctmc.org/api/cameras/{camera_id}/image"
            
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            ny_tz = pytz.timezone('America/New_York')
            now = datetime.now(ny_tz)
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            
            safe_name = "".join(c if c.isalnum() else "_" for c in camera_name)
            
            filename = f"data/{safe_name}/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/{timestamp}_{camera_id}.jpg"
            
            img_byte_arr = io.BytesIO()
            try:
                img = Image.open(io.BytesIO(response.content))
            except IOError as e:
                logger.error(f"Error opening image for {camera_name} ({camera_id}): {e}")
                return f"Error: {camera_name}: Corrupted image data"
            
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(img_byte_arr, format='JPEG', quality=85)
            logger.info(f"Successfully processed image for {camera_name} ({camera_id})")
            img_byte_arr = img_byte_arr.getvalue()

            blob = bucket.blob(filename)
            blob.upload_from_string(img_byte_arr, 'image/jpeg')
            
            logger.info(f"Successfully scraped and uploaded image for {camera_name} ({camera_id}) to gs://{BUCKET_NAME}/{filename}")
            print(f"Image saved to: gs://{BUCKET_NAME}/{filename}")
            time.sleep(0.2) # Add a 0.2-second sleep
            return filename

        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {i + 1} of {retries} failed for camera {camera_name} ({camera_id}): {e}")
            if i < retries - 1:
                time.sleep(2) # Sleep for 2 seconds before retrying
            else:
                logger.error(f"All retries failed for camera {camera_name} ({camera_id})")
                return None
        except IOError as e:
            logger.error(f"Error opening image for {camera_name} ({camera_id}): {e}")
            return None
    
    return None

def scrape_all_cameras(event, context):
    """
    Cloud Function that scrapes a list of cameras.
    """
    try:
        logger.info(f"Function started. Message ID: {context.event_id}")

        # Fetch all cameras
        url = "https://webcams.nyctmc.org/api/cameras"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        all_cameras = response.json()
        logger.info(f"Fetched {len(all_cameras)} cameras from API.")

        cameras_to_scrape = all_cameras
        central_park_camera = {
            "name": "Central Park @ 72nd St Post 37",
            "id": "3f04a686-f97c-4187-8968-cb09265e08ff"
        }
        # Add Central Park camera if it's not already in the list
        if not any(c['id'] == central_park_camera['id'] for c in cameras_to_scrape):
            cameras_to_scrape.append(central_park_camera)
        logger.info(f"Will attempt to scrape {len(cameras_to_scrape)} cameras.")

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)

        
        scraped_files = []
        scraped_count = 0
        total_cameras = len(cameras_to_scrape)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor: # Reduced to 4
            future_to_camera = {executor.submit(download_and_process_camera, camera, bucket): camera for camera in cameras_to_scrape}
            for future in concurrent.futures.as_completed(future_to_camera):
                result = future.result()
                scraped_count += 1
                print(f"Progress: {scraped_count}/{total_cameras} cameras scraped.")
                if result: # If result is not None, it's a successful filename
                    scraped_files.append(result)
                    logger.info(f"Successfully scraped: {result}")
                else:
                    camera_name = future_to_camera[future]['name']
                    logger.warning(f"Failed to scrape a camera: {camera_name}")
        
        logger.info("Overall scraping process complete.")
        create_file_index_gcs(BUCKET_NAME, scraped_files) # Call the new function with scraped_files
        return "Scraping complete.", 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Fatal error fetching camera list: {e}")
        return "Error: " + str(e), 500

def create_file_index_gcs(bucket_name, scraped_files):
    """
    Builds an index of newly scraped files in the GCS bucket and saves it as a JSON object.
    """
    try:
        logger.info("Starting to build file index in GCS from newly scraped files.")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Sort files for consistency
        scraped_files.sort()
        
        index = {
            'files': scraped_files,
            'total_files': len(scraped_files),
            'last_updated': datetime.now(pytz.timezone('America/New_York')).isoformat()
        }

        index_blob = bucket.blob('metadata/file_index.json')
        index_blob.upload_from_string(json.dumps(index, indent=2), 'application/json')

        logger.info(f"Successfully created a new index at gs://{bucket_name}/metadata/file_index.json with {len(scraped_files)} files from current scrape.")

    except (storage.exceptions.GoogleCloudError, json.JSONDecodeError) as e:
        logger.error(f"Error creating file index in GCS: {e}")

if __name__ == "__main__":
    # This is for local testing.
    # It requires credentials to be set up, e.g., by running `gcloud auth application-default login`.
    
    # Mock event and context
    mock_event = {}
    
    class MockContext:
        def __init__(self):
            self.event_id = 'local-test-event'

    mock_context = MockContext()
    
    print("Running local test of scrape_all_cameras...")
    result, status_code = scrape_all_cameras(mock_event, mock_context)
    print(f"Test finished with status {status_code}: {result}")