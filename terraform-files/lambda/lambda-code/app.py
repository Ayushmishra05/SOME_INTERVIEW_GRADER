import boto3
import os
import awsgi
import json
from flask import Flask, request, jsonify
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')  # Set in Lambda env

@app.route('/start-upload', methods=['POST'])
def start_upload():
    data = request.get_json()
    filename = data['filename']
    content_type = data.get('content_type', 'application/octet-stream')

    try:
        logging.info(f"Starting upload for file: {filename}")
        response = s3.create_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=filename,
            ContentType=content_type
        )
        return jsonify({
            'upload_id': response['UploadId'],
            'key': filename
        })
    except ClientError as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get-presigned-urls', methods=['POST'])
def get_presigned_urls():
    data = request.get_json()
    upload_id = data['upload_id']
    key = data['key']
    parts = data['parts']  # Number of parts

    try:
        urls = []
        for part_number in range(1, parts + 1):
            url = s3.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': key,
                    'UploadId': upload_id,
                    'PartNumber': part_number
                },
                ExpiresIn=3600
            )
            urls.append({
                'part_number': part_number,
                'url': url
            })

        return jsonify({'urls': urls})
    except ClientError as e:
        return jsonify({'error': str(e)}), 500


@app.route('/complete-upload', methods=['POST'])
def complete_upload():
    data = request.get_json()
    key = data['key']
    upload_id = data['upload_id']
    parts = data['parts']  # List of {ETag, PartNumber}

    try:
        response = s3.complete_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        return jsonify({'location': response['Location']})
    except ClientError as e:
        return jsonify({'error': str(e)}), 500

def lambda_handler(event, context):
    return awsgi.response(app, event, context)
