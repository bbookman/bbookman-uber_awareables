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

# Bee API configuration
BEE_API_KEY = os.getenv("BEE_API_KEY")
BEE_ROOT_URL = os.getenv("BEE_ROOT_URL", "https://api.bee.computer")
BEE_CONVERSATIONS_ENDPOINT = os.getenv("BEE_CONVERSATIONS_ENDPOINT", "/v1/me/conversations")
BEE_OUTPUT_TARGET = os.getenv("BEE_OUTPUT_TARGET", "./bee")

# Vector storage configuration
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./vector_db")
MARKDOWN_OUTPUT_PATH = os.getenv("MARKDOWN_OUTPUT_PATH", "./markdown_output")

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")