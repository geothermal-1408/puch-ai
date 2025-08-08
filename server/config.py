import os
from dotenv import load_dotenv

load_dotenv()  # read .env in project root

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "abc123token")
MY_NUMBER = os.getenv("MY_NUMBER", "")  #919876543210
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

# Basic validation of critical values
if not MY_NUMBER:
    print("WARNING: MY_NUMBER not set in .env. /mcp/validate will fail unless you set it.")
