# Bike Crowding

This project collects bike traffic data from NYC webcams. It consists of a Google Cloud Function that scrapes images from NYC webcams.

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

3.  **Install the dependencies for the scraper service:**
    ```bash
    pip install -r single-scraper/requirements.txt
    ```

## Services

### Webcam Scraper Service

The `webcam-scraper-v2` service is a Google Cloud Function that scrapes images from the NYC DOT traffic cameras. It is triggered by messages published to the `single-webcam-trigger` Pub/Sub topic.

The service performs the following steps:

1.  **Fetches Camera List:** Retrieves the list of all available cameras from the NYC TMC API.
2.  **Concurrent Image Scraping:** Uses a `ThreadPoolExecutor` with 4 workers to concurrently:
    -   Download the current image for each camera.
    -   Includes a retry mechanism (3 retries with a 2-second sleep between retries) for API calls to handle transient failures.
    -   Compresses the image to save storage space.
    -   Saves the image to a Google Cloud Storage bucket.
    -   Introduces a 0.2-second sleep after each successful scrape to reduce load on the API.
3.  **Incremental File Indexing:** After all cameras are processed, it builds and updates an index of all available files in the GCS bucket. This process is:
    -   **Incremental:** It loads the existing `metadata/file_index.json` (if present) and only adds new files.
    -   **Date-Filtered:** It primarily focuses on indexing files created within the last day to optimize performance.
    -   **Parallelized:** Uses a `ThreadPoolExecutor` with 4 workers to list and process files for each camera in parallel, significantly speeding up the indexing process.
    -   **Progressive:** Logs progress during the indexing process.
4.  **Updates GCS Index:** The generated JSON index is saved to `gs://nyc-webcam-capture/metadata/file_index.json`.

#### Deployment

To deploy the `webcam-scraper-v2` service to Google Cloud, you can run the `deploy.sh` script:

```bash
sh deploy.sh
```

Alternatively, you can run the following command directly:

```bash
gcloud functions deploy webcam-scraper-v2 --source=single-scraper --runtime=python312 --trigger-topic=single-webcam-trigger --entry-point=scrape_all_cameras --region=us-east1
```

The function is triggered by messages published to the `single-webcam-trigger` Pub/Sub topic.
