import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")
XAI_API_KEY = os.getenv("XAI_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

def validate_env_vars():
    required_vars = [
        "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT",
        "ALPACA_API_KEY", "ALPACA_API_SECRET", "XAI_API_KEY", "ALPHA_VANTAGE_API_KEY"
    ]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Required environment variable {var} not found in .env file")