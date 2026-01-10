# Single Scraper

This Cloud Function scrapes images from NYC Traffic Management Center webcams and stores them in Google Cloud Storage.

## Configuration

- **Target Bucket**: `nyc-webcam-capture`
  - *Note: This was previously referred to as 'bike-crowding' in some contexts, but the correct GCS bucket name is `nyc-webcam-capture`.*
- **Timezone**: America/New_York

## Deployment Configuration

For the scraper to run successfully (processing ~1000 cameras), the Cloud Function requires specific resource allocations:

- **Timeout**: `540s` (9 minutes) - Increased from default 60s to handle the volume.
- **Memory**: `1024MB` (1GB) - Provides necessary CPU power.
- **Concurrency**: `max_workers=8` - Tuned to balance speed vs. server load (prevents DOS).

*See `deploy.sh` for the exact `gcloud` command.*

## Data Structure

Images are stored using the following hierarchy:

```
gs://nyc-webcam-capture/data/{Camera_Name}/{Year}/{Month}/{Day}/{Hour}/{Timestamp}_{CameraID}.jpg
```

## File Indexing

The scraper maintains a cumulative daily index of file paths to facilitate efficient retrieval without listing thousands of blobs.

- **Index Path**: `gs://nyc-webcam-capture/metadata/daily_index/YYYY-MM-DD.json`
  - To find the **latest** index, look for the file corresponding to the current date (e.g., `2026-01-10.json`).
  - *Note: The legacy `metadata/file_index.json` is no longer updated.*
- **Format**:
  ```json
  {
    "date": "2026-01-10",
    "files": [
      "data/Camera_A/.../image1.jpg",
      "data/Camera_B/.../image2.jpg"
    ],
    "last_updated": "2026-01-10T16:00:00-05:00"
  }
  ```
- **Updates**: The script *appends* newly scraped files to the current day's index file on every run.

## Web App Integration

For applications visualizing or searching this data:

1.  **Do NOT list buckets**: Listing the `data/` directory is slow and expensive.
2.  **Use the Index**: The daily index is self-sufficient. Run your app by fetching `gs://nyc-webcam-capture/metadata/daily_index/{YYYY-MM-DD}.json` directly.
3.  **Search**: Parse the `files` array in the JSON index. It contains sorted paths to all images scraped that day.
    - *Example*: To find "Central Park", filter the `files` list for the camera name substring.

## Known Limitations

- **Camera Count**: The NYCTMC API currently limits responses to **1024 unique cameras**. Pagination parameters are ignored by the API. As a result, the scraper only captures this specific subset of cameras.
- **Monitoring**: Logs now emit a summary line `Scraping summary: Total=..., Success=..., Failed=..., Duration=...` at the end of each run. Use this for health checks.

## Development

### Environment Notes

- **Bucket Name**: `nyc-webcam-capture` (Do not confuse with `bike-crowding`).
- **Python Version**: 3.14 (running in `venv`).
- **Dependencies**: 
  - `google-cloud-storage` library is used.
  - Exception handling requires `google.cloud.exceptions` (e.g. `GoogleCloudError`), NOT `google.cloud.storage.exceptions`.

### Testing

Unit tests are located in `tests/`.

To run tests locally, ensure you are in the project root:

```bash
# Correct way to run tests (handles sys.path correctly)
venv/bin/python3 single-scraper/tests/test_indexing.py
```

*Note: The test file modifies `sys.path` to allow importing `main.py` from the parent directory.*
