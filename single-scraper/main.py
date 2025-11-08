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

BUCKET_NAME = 'nyc-webcam-capture'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def download_and_process_camera(camera, bucket):
    """
    Downloads and processes a single camera image.
    """
    camera_name = camera.get("name")
    camera_id = camera.get("id")
    logger.info(f"Attempting to scrape camera: {camera_name} ({camera_id})")
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
        img = Image.open(io.BytesIO(response.content))
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(img_byte_arr, format='JPEG', quality=85)
        logger.info(f"Successfully processed image for {camera_name} ({camera_id})")
        img_byte_arr = img_byte_arr.getvalue()

        blob = bucket.blob(filename)
        blob.upload_from_string(img_byte_arr, 'image/jpeg')
        
        logger.info(f"Successfully scraped and uploaded image for {camera_name} ({camera_id}) to gs://{BUCKET_NAME}/{filename}")
        return f"Success: {camera_name}"

    except Exception as e:
        logger.error(f"Error processing camera {camera_name} ({camera_id}): {e}")
        return f"Error: {camera_name}: {e}"

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

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_camera = {executor.submit(download_and_process_camera, camera, bucket): camera for camera in cameras_to_scrape}
            for future in concurrent.futures.as_completed(future_to_camera):
                result = future.result()
                logger.info(result)
        
        logger.info("Overall scraping process complete.")
        create_file_index_gcs(BUCKET_NAME) # Call the new function
        return "Scraping complete.", 200

    except Exception as e:
        logger.error(f"Fatal error in scrape_all_cameras function: {e}")
        return "Error: " + str(e), 500

def list_blobs_for_camera(camera, bucket, one_day_ago, existing_files):
    """
    Lists blobs for a single camera and filters them by date.
    """
    new_files = []
    safe_name = "".join(c if c.isalnum() else "_" for c in camera['name'])
    prefix = f"data/{safe_name}/"
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.time_created > one_day_ago:
            if blob.name not in existing_files:
                new_files.append(blob.name)
    return new_files

def create_file_index_gcs(bucket_name):
    """
    Builds an index of all available files in the GCS bucket from the past day and saves it as a JSON object.
    """
    try:
        logger.info("Starting to build file index in GCS for the past day.")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Load existing index if it exists
        existing_files = set()
        index_blob = bucket.blob('metadata/file_index.json')
        if index_blob.exists():
            try:
                existing_index = json.loads(index_blob.download_as_string())
                existing_files = set(existing_index.get('files', []))
                logger.info(f"Loaded existing index with {len(existing_files)} files.")
            except json.JSONDecodeError:
                logger.warning("Could not decode existing index file. Starting from scratch.")

        # Fetch all cameras
        url = "https://webcams.nyctmc.org/api/cameras"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        all_cameras = response.json()
        logger.info(f"Fetched {len(all_cameras)} cameras for indexing.")

        now = datetime.now(pytz.utc)
        one_day_ago = now - timedelta(days=1)
        
        new_files = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_camera = {executor.submit(list_blobs_for_camera, camera, bucket, one_day_ago, existing_files): camera for camera in all_cameras}
            for future in concurrent.futures.as_completed(future_to_camera):
                try:
                    files = future.result()
                    new_files.extend(files)
                except Exception as exc:
                    camera_name = future_to_camera[future]['name']
                    logger.error(f"Error processing camera {camera_name}: {exc}")

        logger.info(f"Found {len(new_files)} new files from the past day.")

        # Merge and save the index
        all_files = sorted(list(existing_files) + new_files)
        index = {
            'files': all_files,
            'total_files': len(all_files),
            'last_updated': datetime.now(pytz.timezone('America/New_York')).isoformat()
        }

        index_blob.upload_from_string(json.dumps(index, indent=2), 'application/json')

        logger.info(f"Successfully updated metadata/file_index.json with {len(all_files)} files.")

    except Exception as e:
        logger.error(f"Error creating file index in GCS: {e}")