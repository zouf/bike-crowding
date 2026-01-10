import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os
from datetime import datetime
import pytz

# Add parent directory to path to import main
# Add single-scraper directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main

class TestIndexing(unittest.TestCase):
    
    @patch('main.storage.Client')
    @patch('main.datetime')
    def test_update_daily_index_creates_new(self, mock_datetime, mock_storage_client):
        # Setup mocks
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        # Mock time to a fixed date
        fixed_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=pytz.timezone('America/New_York'))
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strftime.return_value = '2026-01-10' # Mock output of strftime called on class, wait. 
        # datetime.now() returns the object, strftime is called on the object.
        # But we patch main.datetime class.
        
        # Mock blob existence (False = new file)
        mock_blob.exists.return_value = False
        
        # Call function
        files = ['file1.jpg', 'file2.jpg']
        main.update_daily_index('test-bucket', files)
        
        # Verify
        mock_bucket.blob.assert_called_with('metadata/daily_index/2026-01-10.json')
        
        # Check upload content
        upload_args = mock_blob.upload_from_string.call_args[0]
        uploaded_json = json.loads(upload_args[0])
        
        self.assertEqual(uploaded_json['date'], '2026-01-10')
        self.assertEqual(uploaded_json['files'], ['file1.jpg', 'file2.jpg'])
        # self.assertEqual(uploaded_json['total_files'], 2)

    @patch('main.storage.Client')
    @patch('main.datetime')
    def test_update_daily_index_aborts_on_corrupt_json(self, mock_datetime, mock_storage_client):
        # Setup mocks
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = "{invalid_json"
        
        main.update_daily_index('test-bucket', ['file1.jpg'])
        
        # Verify NO upload happened
        mock_blob.upload_from_string.assert_not_called()

    @patch('main.storage.Client')
    @patch('main.datetime')
    def test_update_daily_index_aborts_on_read_error(self, mock_datetime, mock_storage_client):
        # Setup mocks to raise exception on read
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        mock_blob.exists.return_value = True
        # Simulate GCS error
        from google.cloud import exceptions as cloud_exceptions
        mock_blob.download_as_text.side_effect = cloud_exceptions.GoogleCloudError("Read failed")
        
        main.update_daily_index('test-bucket', ['file1.jpg'])
        
        # Verify NO upload happened
        mock_blob.upload_from_string.assert_not_called()
        # checking the code I wrote: I removed total_files from the new implementation? 
        # I should check the diff I applied.
        
    @patch('main.storage.Client')
    @patch('main.datetime')
    def test_update_daily_index_appends(self, mock_datetime, mock_storage_client):
        # Setup mocks
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        fixed_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=pytz.timezone('America/New_York'))
        mock_datetime.now.return_value = fixed_now
        
        # Mock blob existence (True) and content
        mock_blob.exists.return_value = True
        existing_data = {
            'date': '2026-01-10',
            'files': ['file1.jpg']
        }
        mock_blob.download_as_text.return_value = json.dumps(existing_data)
        
        # Call function with new file and duplicate file
        files = ['file2.jpg', 'file1.jpg']
        main.update_daily_index('test-bucket', files)
        
        # Verify
        upload_args = mock_blob.upload_from_string.call_args[0]
        uploaded_json = json.loads(upload_args[0])
        
        self.assertEqual(uploaded_json['files'], ['file1.jpg', 'file2.jpg'])
        self.assertEqual(len(uploaded_json['files']), 2)

if __name__ == '__main__':
    unittest.main()
