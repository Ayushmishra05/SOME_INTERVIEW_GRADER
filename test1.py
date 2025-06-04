import openai

def validate_api_key(api_key: str) -> bool:
    openai.api_key = api_key
    try:
        openai.Model.list()
        return True
    except Exception:
        return False

if __name__ == "__main__":
    key = input("Enter OpenAI API key: ").strip()
    if validate_api_key(key):
        print("API key is VALID ✅")
    else:
        print("API key is INVALID ❌")