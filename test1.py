import openai
from dotenv import load_dotenv 
import os 

load_dotenv
api_key = os.environ['OPENAI_API_KEY']

def check_openai_api_key() -> bool:
    """
    Checks if the provided OpenAI API key is valid.
    Returns True if valid, False otherwise.
    """
    openai.api_key = api_key
    try:
        # Make a simple request to test the key
        models = openai.models.list()
        print("✅ API key is valid.")
        return True
    except Exception as e:
        print(f"⚠️ Error occurred: {e}")
        return False


if __name__ == "__main__":
    check_openai_api_key()
