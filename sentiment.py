from datetime import datetime, timedelta, timezone
from xai_sdk.chat import user, system
from clients import xai_client, reddit
from utils import clean_text, check_post_history
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
def get_reddit_sentiment(subreddit, limit, file):
    """Analyze sentiment from Reddit posts using xAI Grok"""
    print(f"Fetching sentiment from r/{subreddit}...")
    
    subreddit_obj = reddit.subreddit(subreddit)
    posts = list(subreddit_obj.search(f"flair:'DD'", sort='new', time_filter="week", limit=limit))

    # Time filter: only posts from the last `hours`
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    num_posts = 0

    # Time complexity: O(n) where n is number of posts
    for post in posts:
        try:
            # Check if post already processed
            if check_post_history(post.id, file):
                print(f"Skipping already processed post: {post.id} - {post.title}")
                continue

            # Clean and combine title and body text
            full_text = clean_text(post.title + ' ' + post.selftext)

            # Perform sentiment analysis using Grok API first
            print(f"Analyzing post with Grok 3 Mini: {post.title}")
            sentiment_data = get_grok_sentiment(full_text)
            
            # Get tickers from Grok analysis
            grok_ticker = sentiment_data.get("ticker")

            # If Grok didn't find a ticker, skip this post
            if not grok_ticker:
                continue
            
            # Capitalize ticker
            grok_ticker = grok_ticker.upper()
            
            compound_score = sentiment_data["compound"]
            confidence = sentiment_data.get("confidence", 1.0)

            # Weight the sentiment by confidence
            weighted_score = compound_score * confidence

            # Buy/sell stock based on sentiment

            # Append individual post data to file
            try:
                # Read existing data
                try:
                    with open(file, 'r') as f:
                        existing_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    existing_data = {}
                
                # Add new post data to existing structure
                if grok_ticker not in existing_data:
                    existing_data[grok_ticker] = {
                        'score': 0,
                        'post_count': 0,
                        'posts': []
                    }
                
                # Append the new post
                existing_data[grok_ticker]['posts'].append({
                    'title': post.title[:100],
                    'sentiment': sentiment_data['sentiment'],
                    'score': compound_score,
                    'confidence': confidence,
                    'post_id': post.id
                })
                
                # Update count and IDs
                existing_data[grok_ticker]['post_count'] += 1

                # Recalculate average score
                if existing_data[grok_ticker]['score'] == 0:
                    existing_data[grok_ticker]['score'] = weighted_score
                else:
                    total_score = sum(p['score'] for p in existing_data[grok_ticker]['posts'])
                    existing_data[grok_ticker]['score'] = round(total_score / existing_data[grok_ticker]['post_count'], 2)
                
                # Write back to file
                with open(file, 'w') as f:
                    json.dump(existing_data, f, indent=4)
                    
            except Exception as e:
                print(f"Error writing to file: {e}")

            num_posts += 1
            
            # Print progress
            if num_posts % 10 == 0:
                print(f"Processed {num_posts} posts...")

            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error processing post: {e}")
            continue

    print(f"Completed sentiment analysis for {num_posts} posts.")
