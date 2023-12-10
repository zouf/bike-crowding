from flask import Flask, render_template, send_file,  send_from_directory
import numpy as np
import pandas as pd
from google.cloud import storage
import datetime
import dateutil.parser
import json

app = Flask(__name__)

# Replace these values with your own
BUCKET_NAME = "bike-crowding"
DATA_FILE_NAME = "logs/central_park.csv"


@app.route("/")
def plot_data():
    # Download data from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(DATA_FILE_NAME)
    with open("/tmp/data.csv", "wb") as f:
        blob.download_to_file(f)

    df = pd.read_csv('/tmp/data.csv', names=['timestamp','raw_count', 'location'])[['timestamp','raw_count']]
    df = df.assign(timestamp=pd.to_datetime(df['timestamp']), raw_count=pd.to_numeric(df['raw_count']))
    df  =df.set_index('timestamp')
    avg_count = np.round(df['raw_count'].median())
    dfs = df.resample("60min").mean().reset_index()
    max_count = dfs['raw_count'].fillna(0).max()
    peak_time_utc = pd.to_datetime(dfs[dfs['raw_count'] == max_count].timestamp.values[0], utc=True).tz_convert('US/Eastern')

    latest_count = np.round(dfs['raw_count'].values[-1])

    dfs['timestamp'] = dfs.timestamp.map(lambda x: x.isoformat())
    LIMIT=100
    data = dfs[['timestamp','raw_count']].to_dict('records')[-LIMIT:]
    return render_template("index.html", data=data, peak_time=peak_time_utc, max_count=np.round(max_count), avg_count=avg_count, latest_count=latest_count)

@app.route("/bike.js")
def serve_bike_js():
    return send_from_directory("static", "bike.js")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
