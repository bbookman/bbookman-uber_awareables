import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configuration for the application
LIMITLESS_INCLUDE_MARKDOWN = os.getenv("LIMITLESS_INCLUDE_MARKDOWN", "true").lower() == "true"
LIMITLESS_INCLUDE_HEADINGS = os.getenv("LIMITLESS_INCLUDE_HEADINGS", "false").lower() == "true"
LIMITLESS_OUTPUT_TARGET = os.getenv("LIMITLESS_OUTPUT_TARGET", "./limitless")
LIMITLESS_API_KEY = os.getenv("LIMITLESS_API_KEY")
LIMITLESS_ROOT_URL = os.getenv("LIMITLESS_ROOT_URL", "https://api.limitless.ai")
LIMITLESS_V1_LIFELOGS_ENDPOINT = os.getenv("LIMITLESS_V1_LIFELOGS_ENDPOINT", "/v1/lifelogs")
JSON_TEST = os.getenv("JSON_TEST", "false").lower() == "true"