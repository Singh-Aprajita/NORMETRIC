
import os

from dotenv import load_dotenv
from google import genai

# Load API key from project .env file
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=API_KEY)

# Use a model available on your free tier.
MODEL_NAME = "gemini-3.1-flash-lite"


def test_ai_connection():
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="Reply with exactly: NORMETRIC AI connected successfully!"
    )

    return response.text
