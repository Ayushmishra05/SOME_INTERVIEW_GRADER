import json 
import boto3
client = boto3.client("secretsmanager", region_name="ap-south-1")

response = client.get_secret_value(SecretId="groq/groq-key")
api_key = response["SecretString"].split(":")[1].replace('}' , '')
# print(api_key)
