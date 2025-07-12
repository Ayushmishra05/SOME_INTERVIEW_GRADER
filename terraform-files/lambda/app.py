import awsgi
from flask import (
    Flask,
    jsonify,
)

app = Flask(__name__)


@app.route("/test", methods=["GET", "POST"])
def index():
    return jsonify(status=200, message='test successful')


def lambda_handler(event, context):
    if 'httpMethod' not in event:
        return {
            "statusCode": 400,
            "body": "test failed"
        }
    return awsgi.response(app, event, context)