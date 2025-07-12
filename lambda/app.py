from flask import Flask, request, jsonify
import boto3
import os
from botocore.client import Config

app = Flask(__name__)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "test-video-upload-some")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

s3_client = boto3.client(
    "s3",
    region_name=REGION,
    config=Config(s3={"use_accelerate_endpoint": True})  # Optional, for transfer acceleration
)

@app.route("/")
def health():
    return {"message": "Flask backend is live"}

@app.route("/start-upload", methods=["POST"])
def start_upload():
    body = request.json
    filename = body["filename"]
    part_count = int(body["part_count"])

    response = s3_client.create_multipart_upload(Bucket=BUCKET_NAME, Key=filename)
    upload_id = response["UploadId"]

    presigned_urls = []
    for part_num in range(1, part_count + 1):
        url = s3_client.generate_presigned_url(
            ClientMethod='upload_part',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': filename,
                'UploadId': upload_id,
                'PartNumber': part_num
            },
            ExpiresIn=3600
        )
        presigned_urls.append({
            "partNumber": part_num,
            "url": url
        })

    return jsonify({
        "uploadId": upload_id,
        "presignedUrls": presigned_urls
    })


@app.route("/complete-upload", methods=["POST"])
def complete_upload():
    body = request.json
    filename = body["filename"]
    upload_id = body["uploadId"]
    parts = body["parts"]  # List of {ETag, PartNumber}

    result = s3_client.complete_multipart_upload(
        Bucket=BUCKET_NAME,
        Key=filename,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts}
    )

    return jsonify({
        "message": "Upload complete",
        "location": result.get("Location")
    })
