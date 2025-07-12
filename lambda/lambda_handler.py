import awsgi
from app import app

def lambda_handler(event, context):
    return awsgi.handle_request(app, event, context)