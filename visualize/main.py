import datetime as dt

import numpy as np
import pandas as pd
from flask import Flask, abort, render_template, request, send_file, send_from_directory
from google.cloud import storage

app = Flask(__name__)

# Replace these values with your own
BUCKET_NAME = "bike-crowding"
DATA_FILE_NAME = "logs/central_park.csv"


@app.route("/raw/<path:path>")
def serve_raw_file(path):
    # Extract filename and date from path
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"/home/mattzouf/bike-crowding/raw/{path}")
    if blob.exists():
        # Download and send the file
        with open("/tmp/image.jpg", "wb") as f:
            blob.download_to_file(f)
        return send_file("/tmp/image.jpg", mimetype="image/jpg")
    else:
        # Return 404 Not Found
        return abort(404)


@app.route("/")
def plot_data():
    # Extract window size from URL parameter
    try:
        window_size = int(request.args.get("window_size"))
    except (TypeError, ValueError):
        window_size = 2  # Default window size

    try:
        smoothing_minutes = int(request.args.get("smoothing_minutes"))
    except (TypeError, ValueError):
        smoothing_minutes = 60  # Default smoothing
    smoothing_minutes = min(max(smoothing_minutes, 1), 360)
    window_size = max(window_size, 2)
    date_range_max = dt.datetime.now().strftime("%Y%m%d")
    min_day = dt.datetime.today() - dt.timedelta(days=window_size)
    date_range_min = min_day.strftime("%Y%m%d")

    # Download data from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(DATA_FILE_NAME)
    with open("/tmp/data.csv", "wb") as f:
        blob.download_to_file(f)

    df = pd.read_csv("/tmp/data.csv", names=["timestamp", "raw_count", "location"])
    # remove ms. to_datetime does not have a good time with this
    df["timestamp"] = df["timestamp"].apply(lambda x: x.split(".")[0])
    print(df.head())
    df = df.assign(
        timestamp=pd.to_datetime(df["timestamp"], format="%Y-%m-%dT%H:%M:%S"),
        raw_count=pd.to_numeric(df["raw_count"]),
    )

    df = df[df["timestamp"] > min_day]
    df = df.set_index("timestamp")
    avg_count = np.round(df["raw_count"].median())

    dfs = (
        df.resample(f"{smoothing_minutes}min")
        .agg({"raw_count": np.mean, "location": "last"})
        .reset_index()
    )
    max_count = dfs["raw_count"].fillna(0).max()

    def fix_location(x):
        if not x:
            return ""
        rval = request.base_url + "raw" + x.split("raw")[1]
        if not ("127" in request.base_url or "192" in request.base_url):
            rval = rval.replace("http:", "https:")
        return rval

    dfs["location"] = dfs["location"].map(fix_location)
    peak_time_utc = pd.to_datetime(
        dfs[dfs["raw_count"] == max_count].timestamp.values[0],
        utc=True,
        errors="coerce",
        format="mixed",
    ).tz_convert("US/Eastern")
    latest_count = np.round(dfs["raw_count"].values[-1])
    dfs["timestamp"] = dfs.timestamp.map(lambda x: x.isoformat())
    dfs["raw_count"] = np.round(dfs["raw_count"])
    img_url = dfs["location"].values[-1]
    data = dfs[["timestamp", "raw_count", "location"]].to_dict("records")
    return render_template(
        "index.html",
        data=data,
        peak_time=peak_time_utc,
        max_count=np.round(max_count),
        avg_count=avg_count,
        latest_count=latest_count,
        window_size=window_size,
        date_range_min=date_range_min,
        date_range_max=date_range_max,
        smoothing_minutes=smoothing_minutes,
        img_url=img_url,
    )


@app.route("/bike.js")
def serve_bike_js():
    return send_from_directory("static", "bike.js")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
