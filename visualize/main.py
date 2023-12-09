from flask import Flask, render_template, send_file,  send_from_directory
import numpy as np
import pandas as pd
from google.cloud import storage
import datetime
import dateutil.parser
import json
from statistics import mean

app = Flask(__name__)

# Replace these values with your own
BUCKET_NAME = "bike-crowding"
DATA_FILE_NAME = "logs/central_park.csv"


def _rolling_average(data):
    print(vals)
    return mean(vals)



@app.route("/")
def plot_data():
    # Download data from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(DATA_FILE_NAME)
    with open("/tmp/data.csv", "wb") as f:
        blob.download_to_file(f)

    # Read and process data
    LIMIT=20000
    df = pd.read_csv('/tmp/data.csv', names=['timestamp','raw_count', 'location'])[['timestamp','raw_count']][-LIMIT:]
    df = df.assign(timestamp=pd.to_datetime(df['timestamp']), raw_count=pd.to_numeric(df['raw_count']))
    df  =df.set_index('timestamp')

    dfs = df.resample("15min").mean().reset_index()
    dfs['timestamp'] = dfs.timestamp.map(lambda x: x.isoformat())
    data = dfs[['timestamp','raw_count']].to_dict('records')
    return render_template("index.html", data=data)

@app.route("/bike.js")
def serve_bike_js():
    return send_from_directory("static", "bike.js")

if __name__ == "__main__":
    app.run(debug=True)
