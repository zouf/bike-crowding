import functions_framework
import requests
import json
from google.cloud import pubsub_v1
import os

PROJECT_ID = os.getenv('GCP_PROJECT')
TOPIC_ID = "single-webcam-trigger"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

@functions_framework.http
def dispatcher(request):
    """
    HTTP-triggered Cloud Function that fetches a list of cameras
    and publishes a message for each one to a Pub/Sub topic.
    """
    try:
        # Fetch the list of cameras
        url = "https://webcams.nyctmc.org/api/cameras"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        cameras = response.json()

        # Publish a message for each camera
        for camera in cameras:
            message_data = {
                "camera_name": camera.get("name"),
                "camera_id": camera.get("id")
            }
            message_json = json.dumps(message_data)
            message_bytes = message_json.encode("utf-8")

            # When you publish a message, the client returns a future.
            future = publisher.publish(topic_path, data=message_bytes)
            # You can block on the future to wait for the message to be published.
            future.result()

        return f"Published {len(cameras)} messages.", 200

    except Exception as e:
        print(e)
        return "Error: " + str(e), 500
