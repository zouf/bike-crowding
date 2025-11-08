gcloud functions deploy webcam-scraper-v2 --source=single-scraper --runtime=python312 --trigger-http --entry-point=scrape_all_cameras --region=us-east1
