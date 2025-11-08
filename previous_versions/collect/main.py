import functions_framework
import requests
from datetime import datetime
import pytz
import json
import concurrent.futures
import logging
import os
from pathlib import Path
from flask import Flask
from PIL import Image
import imagehash
import base64
import csv
import io

app = Flask(__name__)

BUCKET_NAME='nyc-webcam-capture'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraScraper:
    def __init__(self, is_local=True):
        self.is_local = is_local
        self.ny_tz = pytz.timezone('America/New_York')
        self.image_hashes = {}
        
        if is_local:
            # Create local directories for development
            self.base_dir = Path('downloaded_images')
            self.base_dir.mkdir(exist_ok=True)
        else:
            # Use GCS in production with specific bucket
            from google.cloud import storage
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(BUCKET_NAME)
            self.load_image_hashes()
    
    def load_image_hashes(self):
        """Load image hashes from a JSON file in GCS."""
        try:
            blob = self.bucket.blob('metadata/image_hashes.json')
            if blob.exists():
                self.image_hashes = json.loads(blob.download_as_text())
                logger.info("Loaded image hashes from GCS.")
        except Exception as e:
            logger.error(f"Failed to load image hashes: {e}")

    def save_image_hashes(self):
        """Save image hashes to a JSON file in GCS."""
        try:
            blob = self.bucket.blob('metadata/image_hashes.json')
            blob.upload_from_string(json.dumps(self.image_hashes, indent=2), 'application/json')
            logger.info("Saved image hashes to GCS.")
        except Exception as e:
            logger.error(f"Failed to save image hashes: {e}")

    def get_datetime_path(self):
        """Generate timestamp-based path structure"""
        now = datetime.now(self.ny_tz)
        return f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}"
    
    def get_camera_by_name(self, camera_name):
        """Fetch a single camera by name."""
        all_cameras = self.get_all_cameras()
        for camera in all_cameras:
            if camera['name'] == camera_name:
                return [camera]
        logger.warning(f"Camera with name '{camera_name}' not found.")
        return []

    def get_all_cameras(self):
        """Fetch list of all available cameras from NYC TMC API"""
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch camera list: {e}")
            return []

    def save_file(self, content, filepath, content_type=None):
        """Save file either locally or to GCS"""
        if self.is_local:
            full_path = self.base_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                full_path.write_bytes(content)
            else:
                full_path.write_text(content)
            logger.info(f"Saved file locally: {full_path}")
        else:
            blob = self.bucket.blob(filepath)
            if isinstance(content, str):
                blob.upload_from_string(content, content_type=content_type)
            else:
                blob.upload_from_string(content, content_type=content_type)
            logger.info(f"Uploaded to GCS: gs://{BUCKET_NAME}/{filepath}")

    def download_camera_image(self, camera):
        """Download image from a single camera"""
        try:
            camera_id = camera['id']
            url = f"https://webcams.nyctmc.org/api/cameras/{camera_id}/image"
            
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Calculate image hash
            img = Image.open(io.BytesIO(response.content))
            hash = str(imagehash.average_hash(img))

            # Compare with previous hash
            if self.image_hashes.get(camera_id) == hash:
                return {
                    'camera_id': camera_id,
                    'camera_name': camera['name'],
                    'status': 'skipped',
                    'timestamp': datetime.now(self.ny_tz).strftime('%Y%m%d_%H%M%S')
                }
            
            # Update hash
            self.image_hashes[camera_id] = hash
            
            # Get timestamp for both path and filename
            now = datetime.now(self.ny_tz)
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            
            # Create time-based directory structure
            time_path = self.get_datetime_path()
            
            # Use camera name in path (cleaned of special characters)
            safe_name = "".join(c if c.isalnum() else "_" for c in camera['name'])
            
            # Construct final path: time/camera_name/timestamp_id.jpg
            filename = f"data/{safe_name}/{time_path}/{timestamp}_{camera_id}.jpg"
            
            # Save metadata alongside image
            metadata = {
                'camera_id': camera_id,
                'camera_name': camera['name'],
                'timestamp': timestamp,
                'capture_time': now.isoformat(),
                'url': url,
                'location': camera.get('location', {}),
                'status': 'success'
            }
            
            # Compress the image
            img = Image.open(io.BytesIO(response.content))
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()

            # Save image
            self.save_file(img_byte_arr, filename, 'image/jpeg')
            
            return {
                'camera_id': camera_id,
                'camera_name': camera['name'],
                'camera_name_safe': safe_name,
                'file_path': filename,
                'status': 'success',
                'filename': filename,
                'timestamp': timestamp,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing camera {camera.get('id', 'unknown')}: {e}")
            return {
                'camera_id': camera.get('id', 'unknown'),
                'camera_name': camera.get('name', 'unknown'),
                'status': 'error',
                'error': str(e),
                'camera_name_safe': 'unknown',
                'file_path': '',
                'timestamp': datetime.now(self.ny_tz).strftime('%Y%m%d_%H%M%S')
            }

    def log_results_to_csv(self, results):
        """Append results to a CSV file in GCS."""
        try:
            from google.cloud import storage
            import csv
            import io

            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
            
            # Create a CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header if the file doesn't exist
            blob = bucket.blob('logs/images.csv')
            if not blob.exists():
                writer.writerow(['timestamp', 'camera_id', 'camera_name', 'filename', 'status', 'url', 'location'])
            
            # Write data
            for result in results['details']:
                if result['status'] == 'success':
                    writer.writerow([
                        result['timestamp'],
                        result['camera_id'],
                        result['camera_name'],
                        result['filename'],
                        result['status'],
                        result['metadata']['url'],
                        json.dumps(result['metadata']['location'])
                    ])
                elif result['status'] == 'skipped':
                    writer.writerow([
                        result['timestamp'],
                        result['camera_id'],
                        result['camera_name'],
                        '',
                        result['status'],
                        '',
                        ''
                    ])
                else:
                    writer.writerow([
                        result['timestamp'],
                        result['camera_id'],
                        result['camera_name'],
                        '',
                        result['status'],
                        '',
                        ''
                    ])
            
            # Append to the file in GCS
            blob.upload_from_string(output.getvalue(), 'text/csv')
            logger.info("Logged results to CSV in GCS.")

        except Exception as e:
            logger.error(f"Failed to log results to CSV: {e}")

    def process_all_cameras(self, camera_name=None, max_workers=10):
        """Process all cameras with concurrent execution"""
        if camera_name:
            cameras = self.get_camera_by_name(camera_name)
        else:
            cameras = self.get_all_cameras()
        
        # Get current timestamp for this run
        run_timestamp = datetime.now(self.ny_tz).strftime('%Y%m%d_%H%M%S')
        
        results = {
            'timestamp': run_timestamp,
            'all_cameras': cameras,
            # 'total_cameras': len(cameras),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        if not cameras:
            logger.warning("No cameras found!")
            return results
        
        logger.info(f"Starting to process {len(cameras)} cameras")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_camera = {executor.submit(self.download_camera_image, camera): camera 
                              for camera in cameras}
            
            for future in concurrent.futures.as_completed(future_to_camera):
                result = future.result()
                results['details'].append(result)
                if result['status'] == 'success':
                    results['successful'] += 1
                elif result['status'] == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                logger.info(f"Processed camera {result['camera_name']}: {result['status']}")
        
        # # Save run statistics in time-based path
        # stats_filename = f"metadata/{time_path}/run_statistics/{run_timestamp}_stats.json"
        # self.save_file(
        #     json.dumps(results, indent=2),
        #     stats_filename,
        #     'application/json'
        # )
        
        self.log_results_to_csv(results)

        # Remove metadata from details before saving to JSON
        for detail in results['details']:
            if 'metadata' in detail:
                del detail['metadata']

        stats_filename = f"metadata/latest_status.json"
        self.save_file(
            json.dumps(results, indent=2),
            stats_filename,
            'application/json'
        )
        

        self.save_image_hashes()

        logger.info(f"Completed processing. Success: {results['successful']}, Failed: {results['failed']}, Skipped: {results['skipped']}")
        return results

@functions_framework.cloud_event
def scrape_all_cameras(cloud_event):
    """HTTP Cloud Function to scrape all NYC traffic cameras"""
    topic = cloud_event["source"].split("/")[-1]

    camera_name = None
    if topic == "minute-trigger":
        try:
            data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
            camera_name = json.loads(data).get("camera_name")
        except Exception as e:
            logger.error(f"Failed to parse message data: {e}")

    try:
        # Use production mode by default for cloud deployment
        is_local = os.getenv('ENVIRONMENT', 'production') == 'development'
        scraper = CameraScraper(is_local=is_local)
        results = scraper.process_all_cameras(camera_name=camera_name)
        
        return {
            'status': 'complete',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Fatal error in main function: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


if __name__ == "__main__":
    # For direct Python execution
    scraper = CameraScraper(is_local=True)
    results = scraper.process_all_cameras(max_workers=2)
    print(json.dumps(results, indent=2))