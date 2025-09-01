import boto3  
import json


def get_api_key():
    client = boto3.client("secretsmanager", region_name="ap-south-1")

    response = client.get_secret_value(SecretId="openai/api-key")
    api_key = response["SecretString"].split(":")[1].replace('}' , '')
    api = {
        'api_key' : api_key
    }
    with open(r'utils/openai_key.json' , 'w') as f:
        json.dump(api , fp=f)


def get_groq_key():
    client = boto3.client("secretsmanager", region_name="ap-south-1")

    response = client.get_secret_value(SecretId="groq/groq-key")
    api_key = response["SecretString"].split(":")[1].replace('}' , '')
    api = {
        'api_key' : api_key
    }
    with open(r'utils/groq_key.json' , 'w') as f:
        json.dump(api , fp=f)


# print(api_key , type(api_key))


if __name__ == "__main__":
    get_api_key()
    get_groq_key()

