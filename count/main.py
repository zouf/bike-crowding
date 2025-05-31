import os
import tempfile
from google.cloud import storage
import cv2
import io
import numpy as np
import pandas as pd
from datetime import datetime
import multiprocessing
from functools import lru_cache


@lru_cache
def get_storage_client():
    return storage.Client()

class ParallelBikeDetector:
    def __init__(self, bucket_name, weights_path, cfg_path, names_path):
        """
        Initialize detector with Google Cloud Storage and YOLO
        """
        # self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.weights_path = weights_path
        self.cfg_path = cfg_path
        self.names_path = names_path


    def get_uri_as_bytes(self, uri: str) -> io.BytesIO:
                
        storage_client = get_storage_client()
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(uri)
        
        # Download the file content into a BytesIO object
        file_content = io.BytesIO()
        blob.download_to_file(file_content)
        
        # Seek to the beginning of the BytesIO object so it can be read
        file_content.seek(0)
        
        return file_content


    def _detect_bikes_in_single_image(self, image_uri):
        """
        Detect bikes in a single image
        """
        # Load YOLO for each process
        net = cv2.dnn.readNet(self.weights_path, self.cfg_path)
        
        # Load class names
        with open(self.names_path, 'r') as f:
            classes = [line.strip() for line in f.readlines()]
        
        # Get output layer names
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

        # Read image
        file_content = self.get_uri_as_bytes(image_uri)
        # Read image using cv2 (convert BytesIO to numpy array)
        img_array = np.asarray(bytearray(file_content.read()), dtype=np.uint8)
        
        # Decode image
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # or use cv2.IMREAD_GRAYSCALE for grayscale images
        
        if img is None:
            raise ValueError("Failed to decode image from the provided bytes.")
        
        
        # Prepare image for YOLO
        blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(output_layers)
        print('gs://bike-crowding/'+image_uri)
        # Count bikes
        bike_count = 0
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if classes[class_id] == 'bicycle' and confidence > 0.5:
                    bike_count += 1
        # Parse timestamp from filename
        try:
            filename = os.path.basename(image_uri)
            timestamp_str = filename.split('_')[0]
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d')
        except Exception:
            timestamp = None

        return (image_uri, bike_count, timestamp)

    def process_images_parallel(self, num_cores=None):
        """
        Process images in parallel from downloaded directory
        """

        storage_client = get_storage_client()
        bucket = storage_client.bucket(self.bucket_name)
      
        blobs = list(bucket.list_blobs(prefix='data/Central_Park___72nd_St_Post_37/'))
        image_uris = [x.name for x in blobs if x.name.endswith('.jpg')]

        # Use all available cores if not specified
        if num_cores is None:
            num_cores = multiprocessing.cpu_count()

        results = []
        
        # for image_uri in image_uris:
        #     results.append(self._detect_bikes_in_single_image(image_uri))
        

        with multiprocessing.Pool(num_cores) as pool:
            results = pool.map(self._detect_bikes_in_single_image, image_uris)

    
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['path', 'bike_count', 'timestamp'])
        df = df.dropna(subset=['timestamp'])

        return df

    def analyze_bike_data(self, df):
        """
        Analyze bike detection results
        """
        max_bikes_image = df.loc[df['bike_count'].idxmax()]
        
        df['hour'] = df['timestamp'].dt.hour
        bikes_by_hour = df.groupby('hour')['bike_count'].sum()
        peak_bike_hour = bikes_by_hour.idxmax()
        
        return {
            'most_bikes_image': max_bikes_image['path'],
            'max_bike_count': max_bikes_image['bike_count'],
            'peak_bike_hour': peak_bike_hour,
            'total_bikes': df['bike_count'].sum()
        }

def main():
    # YOLO file paths
    weights_path = 'yolov3.weights'
    cfg_path = 'yolov3.cfg'
    names_path = 'coco.names'
    
    # Google Cloud Storage bucket name
    bucket_name = 'bike-crowding'
    
    # Initialize detector
    detector = ParallelBikeDetector(bucket_name, weights_path, cfg_path, names_path)
    
    # Process images
    bike_data = detector.process_images_parallel()
    
    # Analyze results
    analysis = detector.analyze_bike_data(bike_data)
    
    print("Bike Detection Analysis:")
    print(f"Image with Most Bikes: {analysis['most_bikes_image']}")
    print(f"Maximum Bike Count in Single Image: {analysis['max_bike_count']}")
    print(f"Peak Bike Hour: {analysis['peak_bike_hour']}")
    print(f"Total Bikes Detected: {analysis['total_bikes']}")

if __name__ == "__main__":
    main()
