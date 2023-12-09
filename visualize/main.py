from flask import Flask, render_template, send_file,  send_from_directory

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

    # Read and process data
    bike_data = []
    with open("/tmp/data.csv", "r") as f:
        lines = f.readlines()
        for line in lines[-10000:]:
            # Split line by comma
            values = line.split(",")
            # Parse timestamp
            timestamp = dateutil.parser.parse(values[0]).isoformat()
            # Get raw count
            raw_count = float(values[1])

            # Append data to list
            bike_data.append({
                "datetime": timestamp,
                "raw_count": raw_count,
            })

    # Convert data to D3 format
    # d3_data = json.dumps(bike_data)
    print(bike_data[0])
    # Render template with D3 data
    return render_template("index.html", data=bike_data)

@app.route("/bike.js")
def serve_bike_js():
    return send_from_directory("static", "bike.js")

if __name__ == "__main__":
    app.run(debug=True)
