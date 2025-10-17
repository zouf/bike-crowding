# Bike Crowding

This project collects and analyzes bike traffic data from NYC webcams. It consists of a Google Cloud Function that scrapes images from NYC webcams.

## Getting Started

### Prerequisites

-   Python 3.12 or higher
-   Google Cloud SDK

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/bike-crowding.git
    cd bike-crowding
    ```

2.  **Set up the virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies for the collect service:**
    ```bash
    pip install -r collect/requirements.txt
    ```

## Services

### Collect Service

The `collect` service is a Google Cloud Function that scrapes images from the NYC DOT traffic cameras. It is triggered by Pub/Sub messages from two different Cloud Scheduler jobs:

-   **Hourly Trigger:** Scrapes all cameras every hour.
-   **Minute Trigger:** Scrapes the `Central_Park___72nd_St_Post_37` camera every minute.

The service performs the following steps:

1.  Fetches the list of all cameras from the NYC TMC API.
2.  For each camera, it downloads the current image.
3.  Compresses the image to save storage space.
4.  Calculates a perceptual hash of the image to detect and avoid storing duplicate images.
5.  Saves the image to a Google Cloud Storage bucket.
6.  Logs metadata about the scraping process to a CSV file in the same bucket.

#### Triggers

The function is triggered by two Cloud Scheduler jobs that publish messages to two different Pub/Sub topics.

**1. Hourly Trigger:**

-   **Pub/Sub Topic:** `hourly-trigger`
-   **Cloud Scheduler Job:** Runs every hour and sends an empty message.

**2. Minute Trigger:**

-   **Pub/Sub Topic:** `minute-trigger`
-   **Cloud Scheduler Job:** Runs every minute and sends a message with the following body:
    ```json
    {"camera_name": "Central_Park___72nd_St_Post_37"}
    ```

To create these triggers, you can use the following `gcloud` commands:

```bash
# Hourly Trigger
gcloud pubsub topics create hourly-trigger
gcloud scheduler jobs create pubsub hourly-trigger-job --schedule "0 * * * *" --topic hourly-trigger --message-body "Go" --location us-east1

# Minute Trigger
gcloud pubsub topics create minute-trigger
gcloud scheduler jobs create pubsub minute-trigger-job --schedule "* * * * *" --topic minute-trigger --message-body '{"camera_name": "Central_Park___72nd_St_Post_37"}' --location us-east1
```

#### Local Development

To run the `collect` service locally for testing, you can uncomment the `if __name__ == "__main__":` block at the end of the `collect/main.py` file. This will simulate an hourly trigger and scrape all cameras.

```bash
ENVIRONMENT=development python collect/main.py
```

This will save the images to a local `downloaded_images` directory instead of uploading them to GCS.

#### Deployment

To deploy the `collect` service to Google Cloud with both triggers, run the following command:

```bash
sh deploy.sh
```