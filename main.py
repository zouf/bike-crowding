import os
import cv2
import datetime as dt
from google.cloud import storage

import requests
import time
import json


URL='https://webcams.nyctmc.org/api/cameras/3f04a686-f97c-4187-8968-cb09265e08ff/image'
PROJECT_ID = 'zouf-dev'
BUCKET_NAME = 'bike-crowding'

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)


def get_and_record_image(now: dt.datetime, url: str) -> str:
    response = requests.get(url)
    nowstr = now.strftime('%Y%m%dT%H%M%S')
    ym = now.strftime('%Y%m')
    response.raise_for_status()
    directory = f'/home/mattzouf/bike-crowding/raw/{ym}'
    os.makedirs(directory, exist_ok=True)
    path=f'/home/mattzouf/bike-crowding/raw/{ym}/image.{nowstr}.jpg'
    with open(path,'wb') as fp:
        fp.write(response.content)
    p=upload_blob(BUCKET_NAME, path, 'images/centralpark/{ym}/screenshot.{nowstr}.jpg')
    return path

def main():
    i = 0
    with open('/home/mattzouf/bike-crowding/log.csv', 'a+') as fplog:
        while True:
            now=dt.datetime.utcnow()
            path=get_and_record_image(now, URL)
            image = cv2.imread(path)

            # Convert the image to grayscale
            grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Apply a blur to the image
            blurred_image = cv2.blur(grayscale_image, (5, 5))
            # Apply a threshold to the image
            thresholded_image = cv2.threshold(blurred_image, 127, 255, cv2.THRESH_BINARY)[1]
            # Find the contours in the image
            contours, hierarchy = cv2.findContours(thresholded_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # Find the number of contours
            number_of_people = len(contours)

            # Print the number of people
            data={'time': now.isoformat(), 'number_of_people': str(number_of_people), 'path_to_image': path }
            print(data)
            fplog.write(','.join(list(data.values()))+'\n')
            upload_blob(BUCKET_NAME, '/home/mattzouf/bike-crowding/log.csv', 'logs/central_park.csv')
            time.sleep(15)
            if os.path.exists(path):
                os.remove(path)




if __name__ == '__main__':
    main()

