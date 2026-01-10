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
