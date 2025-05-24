import os
import time
import hashlib
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pathlib import Path

# Load .env từ thư mục cha
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

app = Flask(__name__)

CLOUD_NAME = os.getenv("CLOUD_NAME")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")



def generate_signature(params: dict, api_secret: str) -> str:
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    to_sign = sorted_params + api_secret
    return hashlib.sha1(to_sign.encode("utf-8")).hexdigest()


def upload_to_cloudinary(file_stream):
    timestamp = int(time.time())
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"

    params = {
        "timestamp": timestamp,
    }

    signature = generate_signature(params, API_SECRET)

    payload = {
        "api_key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
    }

    files = {
        "file": file_stream
    }

    response = requests.post(url, data=payload, files=files)

    if response.status_code == 200:
        return response.json()["secure_url"]
    else:
        raise Exception(f"Upload failed: {response.text}")


def upload_image_to_cloudinary(file_stream) -> str:
    timestamp = int(time.time())
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"

    params = {
        "timestamp": timestamp,
    }

    signature = generate_signature(params, API_SECRET)

    payload = {
        "api_key": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
    }

    files = {
        "file": file_stream
    }

    response = requests.post(url, data=payload, files=files)

    if response.status_code == 200:
        return response.json()["secure_url"]
    else:
        raise Exception(f"Upload failed: {response.text}")