import praw
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from xai_sdk import Client
from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
    ALPACA_API_KEY, ALPACA_API_SECRET, XAI_API_KEY
)

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Initialize Alpaca API
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True)
stock_quote_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)

# Initialize xAI Client
xai_client = Client(api_key=XAI_API_KEY)