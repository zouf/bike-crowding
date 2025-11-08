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

The `webcam-scraper-v2` service is a Google Cloud Function that scrapes images from the NYC DOT traffic cameras. It is triggered by HTTP requests.

The service performs the following steps:

1.  Fetches the list of all cameras from the NYC TMC API.
2.  For each camera, it downloads the current image.
3.  Compresses the image to save storage space.
4.  Saves the image to a Google Cloud Storage bucket.

#### Deployment

To deploy the `webcam-scraper-v2` service to Google Cloud, run the following command:

```bash
gcloud functions deploy webcam-scraper-v2 --source=single-scraper --runtime=python312 --trigger-http --entry-point=scrape_all_cameras --region=us-east1
```
