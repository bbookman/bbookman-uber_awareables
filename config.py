import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configuration for the application
LIMITLESS_INCLUDE_MARKDOWN = os.getenv("LIMITLESS_INCLUDE_MARKDOWN", "true").lower() == "true"
LIMITLESS_INCLUDE_HEADINGS = os.getenv("LIMITLESS_INCLUDE_HEADINGS", "false").lower() == "true"
# Using consistent naming for Limitless output target
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

# Markdown output targets
BEE_MD_TARGET = os.getenv("BEE_MD_TARGET", "./md/bee")
LIMITLESS_MD_TARGET = os.getenv("LIMITLESS_MD_TARGET", "./md/limitless")

# Timezone configuration
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

class Config:
    LIMITLESS_INCLUDE_MARKDOWN = LIMITLESS_INCLUDE_MARKDOWN
    LIMITLESS_INCLUDE_HEADINGS = LIMITLESS_INCLUDE_HEADINGS
    LIMITLESS_API_KEY = LIMITLESS_API_KEY
    LIMITLESS_ROOT_URL = LIMITLESS_ROOT_URL
    LIMITLESS_V1_LIFELOGS_ENDPOINT = LIMITLESS_V1_LIFELOGS_ENDPOINT
    JSON_TEST = JSON_TEST

    BEE_API_KEY = BEE_API_KEY
    BEE_ROOT_URL = BEE_ROOT_URL
    BEE_CONVERSATIONS_ENDPOINT = BEE_CONVERSATIONS_ENDPOINT
    BEE_OUTPUT_TARGET = BEE_OUTPUT_TARGET

    VECTOR_DB_PATH = VECTOR_DB_PATH
    MARKDOWN_OUTPUT_PATH = MARKDOWN_OUTPUT_PATH

    BEE_MD_TARGET = BEE_MD_TARGET
    LIMITLESS_MD_TARGET = LIMITLESS_MD_TARGET

    TIMEZONE = TIMEZONE

    OLLAMA_BASE_URL = OLLAMA_BASE_URL
    OLLAMA_MODEL = OLLAMA_MODEL

    def get_vector_store_path(self):
        """Get the path to the vector store."""
        return self.VECTOR_DB_PATH