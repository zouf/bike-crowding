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

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraScraper:
    def __init__(self, is_local=True):
        self.is_local = is_local
        self.ny_tz = pytz.timezone('America/New_York')
        
        if is_local:
            # Create local directories for development
            self.base_dir = Path('downloaded_images')
            self.base_dir.mkdir(exist_ok=True)
        else:
            # Use GCS in production with specific bucket
            from google.cloud import storage
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket('bike-crowding')
    
    def get_datetime_path(self):
        """Generate timestamp-based path structure"""
        now = datetime.now(self.ny_tz)
        return f"{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}"
    
    def get_all_cameras(self):
        """Fetch list of all available cameras from NYC TMC API"""
        try:
            url = "https://webcams.nyctmc.org/api/cameras"
            response = requests.get(url, timeout=10)
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
            logger.info(f"Uploaded to GCS: gs://bike-crowding/{filepath}")

    def download_camera_image(self, camera):
        """Download image from a single camera"""
        try:
            camera_id = camera['id']
            url = f"https://webcams.nyctmc.org/api/cameras/{camera_id}/image"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
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
            
            # Save both image and metadata
            self.save_file(response.content, filename, 'image/jpeg')
            self.save_file(
                json.dumps(metadata, indent=2),
                filename.replace('.jpg', '_metadata.json'),
                'application/json'
            )
            
            return {
                'camera_id': camera_id,
                'camera_name': camera['name'],
                'camera_name_safe': safe_name,

                'file_path': filename,
                'status': 'success',
                'filename': filename,
                'timestamp': timestamp
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

    def process_all_cameras(self, max_workers=10):
        """Process all cameras with concurrent execution"""
        cameras = self.get_all_cameras()
        
        # Get current timestamp for this run
        run_timestamp = datetime.now(self.ny_tz).strftime('%Y%m%d_%H%M%S')
        
        results = {
            'timestamp': run_timestamp,
            'all_cameras': cameras,
            # 'total_cameras': len(cameras),
            'successful': 0,
            'failed': 0,
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
        
        stats_filename = f"metadata/latest_status.json"
        self.save_file(
            json.dumps(results, indent=2),
            stats_filename,
            'application/json'
        )
        

        logger.info(f"Completed processing. Success: {results['successful']}, Failed: {results['failed']}")
        return results

@functions_framework.http
def scrape_all_cameras(request):
    """HTTP Cloud Function to scrape all NYC traffic cameras"""
    try:
        print(request)
        # Use production mode by default for cloud deployment
        is_local = os.getenv('ENVIRONMENT', 'production') == 'development'
        scraper = CameraScraper(is_local=is_local)
        results = scraper.process_all_cameras()
        
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


# if __name__ == "__main__":
#     # For direct Python execution
#     class MockRequest: pass
#     result = scrape_all_cameras(MockRequest())
#     print(json.dumps(result, indent=2))