gcloud functions deploy scrape_all_cameras\
  --runtime=python39 \                                     
  --trigger-topic=hourly-trigger \
  --entry-point=scrape_all_cameras \
  --region=us-east1
