from flask import Flask
import os
import requests
from PIL import Image
import imagehash
import io

app = Flask(__name__)

@app.route('/')
def hello_world():
    try:
        # Create a dummy image
        img = Image.new('RGB', (60, 30), color = 'red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # Calculate image hash
        hash = imagehash.average_hash(Image.open(io.BytesIO(img_byte_arr)))
        return f"Successfully performed image hashing. Hash: {hash}"
    except Exception as e:
        return f"Failed to perform image hashing: {e}"

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))