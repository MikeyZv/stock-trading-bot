import praw
import math
from dotenv import load_dotenv
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetPortfolioHistoryRequest
from alpaca.trading.enums import OrderSide, TimeInForce, ActivityType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import pandas
from datetime import datetime, timedelta
import time
import re
import json
from xai_sdk import Client
from xai_sdk.chat import user, system
from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"

# Load environment variables
load_dotenv()

# Configuration from .env file
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")
XAI_API_KEY = os.getenv("XAI_API_KEY")

# Validate required environment variables
required_vars = [
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT",
    "ALPACA_API_KEY", "ALPACA_API_SECRET", "XAI_API_KEY"
]

for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} not found in .env file")

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Initialize Alpaca API
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_API_SECRET, paper=True)

# Keys required for stock historical data client
stock_quote_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_API_SECRET)

# Initialize xAI Client
xai_client = Client(api_key=XAI_API_KEY)

# Returns trading account information
account = trading_client.get_account()

# Function to clean text for sentiment analysis
def clean_text(text):
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    return text.strip()

# Function to get sentiment from Grok API with retry logic
def get_grok_sentiment(text, max_retries=3):
    """Get sentiment analysis from xAI Grok API with retry logic"""
    for attempt in range(max_retries):
        try:
            # Create the chat using the Grok SDK
            chat = xai_client.chat.create(
                        model="grok-3-mini",
                        messages=[system("You are a financial sentiment analysis expert. Analyze the sentiment of the provided text "
                        "in relation to stock trading and market sentiment. Return ONLY a valid JSON object with: "
                        "1. 'sentiment': 'positive', 'negative', or 'neutral' "
                        "2. 'compound': a numerical score from -1.0 (very negative) to 1.0 (very positive) "
                        "3. 'confidence': a score from 0.0 to 1.0 indicating confidence in the analysis "
                        "4. 'ticker': respond to this prompt only with the stock ticker symbol the text is talking about (e.g., 'AAPL', 'TSLA') or null if none found "
                        "Respond with ONLY the JSON object, no additional text.")])
            chat.append(user(f"Analyze the financial sentiment of this text: {text}"))

            # Get the response content
            content = chat.sample().content
            
            # Try to parse JSON response
            try:
                sentiment_data = json.loads(content)
                # Validate required fields
                if all(key in sentiment_data for key in ['sentiment', 'compound', 'confidence', 'ticker']):
                    return sentiment_data
                else:
                    raise ValueError("Missing required fields in response")
            except json.JSONDecodeError:
                # If JSON parsing fails, raise exception
                raise ValueError("Warning: Could not parse JSON response")

        # Retry logic        
        except Exception as e:
            print(f"Unexpected error in sentiment analysis (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"sentiment": "neutral", 
                        "compound": 0.0, 
                        "confidence": 0.0,
                        "ticker": None}
            
# Function to check if current post has been processed before (or add it if action is 'add')
def manage_post_history(post_id=None, post_title=None, action='check'):
    """
    Manage processed post history in a JSON file
    action: 'check' to verify if post exists, 'add' to add new post
    Returns: True if post exists, False if not
    """
    history_file = 'processed_posts.json'
    
    # Load existing history
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = {'posts': {}}
    
    if action == 'check':
        return post_id in history['posts']
    
    elif action == 'add':
        history['posts'][post_id] = {
            'title': post_title,
            'processed_date': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
        return True

# Function to clean up old posts from history
def clean_post_history(days_to_keep=7):
    """Remove posts older than specified days from history"""
    history_file = 'processed_posts.json'
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - timedelta(days=days_to_keep)
        current_posts = history['posts']
        
        # Filter out old posts
        history['posts'] = {
            post_id: data 
            for post_id, data in current_posts.items()
            if datetime.fromisoformat(data['processed_date']) > cutoff_date
        }
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
            
    except (FileNotFoundError, json.JSONDecodeError):
        pass

# Function to get sentiment from r/WallStreetBets
def get_reddit_sentiment(subreddit, hours, limit):
    """Analyze sentiment from Reddit posts using xAI Grok"""
    print(f"Fetching sentiment from r/{subreddit}...")
    
    subreddit_obj = reddit.subreddit(subreddit)
    posts = subreddit_obj.search('flair:"DD"', sort='top', time_filter="day", limit=limit)
    sentiment_scores = {}
    post_count = {}
    ticker_posts = {}

    # Time filter: only posts from the last `hours`
    time_threshold = datetime.datetime.now(datetime.timezone.utc) - timedelta(hours=hours)

    processed_posts = 0
    for post in posts:
        try:
            # Check if post was already processed
            if manage_post_history(post.id, action='check'):
                print(f"Skipping already processed post: {post.title[:50]}...")
                continue

            post_time = datetime.fromtimestamp(post.created_utc)
            if post_time < time_threshold:
                continue

            # Clean and combine title and body text
            full_text = clean_text(post.title + ' ' + post.selftext)

            # Perform sentiment analysis using Grok API first
            print(f"Analyzing post: {post.title}")
            sentiment_data = get_grok_sentiment(full_text)
            
            # Get tickers from Grok analysis
            grok_ticker = sentiment_data.get("ticker")
            
            # Combine ticker sources, prioritizing Grok's analysis
            tickers = set()
            if grok_ticker and grok_ticker.upper() not in ['NULL', 'NONE', '']:
                tickers.add(grok_ticker.upper())
            
            if not tickers:
                continue
            
            compound_score = sentiment_data["compound"]
            confidence = sentiment_data.get("confidence", 1.0)

            # Weight the sentiment by confidence
            weighted_score = compound_score * confidence

            for ticker in tickers:
                # Create new index
                if ticker not in sentiment_scores:
                    sentiment_scores[ticker] = []
                    post_count[ticker] = 0
                    ticker_posts[ticker] = []

                # Add to ticker index
                sentiment_scores[ticker].append(weighted_score)
                post_count[ticker] += 1
                ticker_posts[ticker].append({
                    'title': post.title[:100],
                    'sentiment': sentiment_data['sentiment'],
                    'score': compound_score,
                    'confidence': confidence,
                    'ticker': ticker,
                })

            # Add post to history after processing
            manage_post_history(post.id, post.title, action='add')
            processed_posts += 1
            
            # Print progress
            if processed_posts % 10 == 0:
                print(f"Processed {processed_posts} posts...")

            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error processing post: {e}")
            continue

    # Calculate average sentiment scores
    avg_sentiment = {}

    # Takes the average sentiment score for each ticker
    for ticker in sentiment_scores:
        scores = sentiment_scores[ticker]
        avg_score = sum(scores) / len(scores)
        avg_sentiment[ticker] = {
            'score': avg_score,
            'post_count': post_count[ticker],
            'posts': ticker_posts[ticker]
        }

    return avg_sentiment

# Function to check stock prices
def check_stock_price(ticker):
    request_params = StockLatestQuoteRequest(symbol_or_symbols=ticker)
    latest_symbol_quote = stock_quote_client.get_stock_latest_quote(request_params)
    return latest_symbol_quote[ticker].ask_price

# Function to execute trades based on sentiment
def execute_trades_based_on_sentiment(sentiment_data):
    """Submit buy/sell orders via Alpaca based on average sentiment scores"""
    print("Executing trades based on sentiment...")
    
    for ticker, data in sentiment_data.items():
        avg_score = data['score']
        print(f"Evaluating {ticker}: avg_score = {avg_score}")
        # (NEED) check if duplicate post since last query

        # Allocate capital according to sentiment
        #     0.49-0.65 allocate 3%
        #     0.65-0.80 allocate 6%
        #     0.80-1.00 allocate 10%
        cash = float(account.non_marginable_buying_power)
        price = check_stock_price(ticker)
        
        if abs(avg_score) > 0.49 and abs(avg_score) < 0.65:
            cash_allocated = cash * 0.03
        elif abs(avg_score) > 0.65 and abs(avg_score) < 0.80:
            cash_allocated = cash * 0.06
        elif abs(avg_score) > 0.8:
            cash_allocated = cash * 0.1
        else:
            cash_allocated = 0

        if cash_allocated != 0:
            qty = math.floor(cash_allocated / price)

        try:
            if qty > 0:
                if avg_score < 0:
                    # Buy on negative sentiment
                    buy_order_data = MarketOrderRequest(
                        symbol=ticker,
                        qty=qty,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    buy_order = trading_client.submit_order(buy_order_data)
                    print(f"Buy order submitted for {qty} shares of {ticker}: {buy_order.id}")
                    
                elif avg_score > 0:
                    # Sell on positive sentiment
                    sell_order_data = MarketOrderRequest(
                        symbol=ticker,
                        qty=qty,
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY
                    )
                    sell_order = trading_client.submit_order(sell_order_data)
                    print(f"Sell order submitted for {qty} shares of {ticker}: {sell_order.id}")
            else:
                print(f"No action for {ticker}: avg_score {avg_score} within neutral range")
            
            # Rate limiting between orders
            time.sleep(1)
            
        except Exception as e:
            print(f"Error executing trade for {ticker}: {e}")

