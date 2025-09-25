from datetime import datetime, timedelta, timezone
from xai_sdk.chat import user, system
from clients import xai_client, reddit
from utils import clean_text, calculate_average_sentiment, check_post_history, add_post_to_history
import json
import time

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

# Function to get sentiment from r/WallStreetBets
def get_reddit_sentiment(subreddit, hours, limit):
    """Analyze sentiment from Reddit posts using xAI Grok"""
    print(f"Fetching sentiment from r/{subreddit}...")
    
    subreddit_obj = reddit.subreddit(subreddit)
    posts = list(subreddit_obj.search(f"flair:'DD'", sort='new', time_filter="week", limit=limit))
    sentiment_scores = {}
    post_count = {}
    ticker_posts = {}

    # Time filter: only posts from the last `hours`
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    num_posts = 0
    for post in posts:
        try:
            # Check if post already processed
            if check_post_history(post.id):
                print(f"Skipping already processed post: {post.id} - {post.title}")
                continue

            # Check post age
            # post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            # if post_time < time_threshold:
            #     print(f"Skipping old post: {post.id} - {post.title}")
            #     continue

            # Clean and combine title and body text
            full_text = clean_text(post.title + ' ' + post.selftext)

            # Perform sentiment analysis using Grok API first
            print(f"Analyzing post using Grok 3 Mini: {post.title}")
            sentiment_data = get_grok_sentiment(full_text)
            
            # Get tickers from Grok analysis
            grok_ticker = sentiment_data.get("ticker")
            
            # Combine ticker
            tickers = set()
            if grok_ticker and grok_ticker.upper() not in ['NULL', 'NONE', '']:
                tickers.add(grok_ticker.upper())
            
            if not tickers or grok_ticker.upper() == "RYCEY":
                continue
            
            compound_score = sentiment_data["compound"]
            confidence = sentiment_data.get("confidence", 1.0)

            # Weight the sentiment by confidence
            weighted_score = compound_score * confidence

            for ticker in tickers:
                # Create empty data entries if ticker not seen before
                if ticker not in sentiment_scores:
                    sentiment_scores[ticker] = []
                    post_count[ticker] = 0
                    ticker_posts[ticker] = []

                # Add to data to ticker
                sentiment_scores[ticker].append(weighted_score)
                post_count[ticker] += 1
                ticker_posts[ticker].append({
                    'title': post.title[:100],
                    'sentiment': sentiment_data['sentiment'],
                    'score': compound_score,
                    'confidence': confidence,
                    'ticker': ticker,
                })
            
            add_post_to_history(post, weighted_score, grok_ticker.upper())
            num_posts += 1
            
            # Print progress
            if num_posts % 10 == 0:
                print(f"Processed {num_posts} posts...")

            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error processing post: {e}")
            continue
    
    return calculate_average_sentiment(sentiment_scores, ticker_posts, post_count)
