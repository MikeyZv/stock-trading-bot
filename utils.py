import re
import json
from datetime import datetime, timezone

# Function to clean text for sentiment analysis
def clean_text(text):
    text = re.sub(r'http\S+', '', text)  # Replace URLs with empty string
    return text.strip() # Remove leading/trailing whitespace

# Function to calculate average sentiment scores 
def calculate_average_sentiment(sentiment_scores, ticker_posts, post_count):
    """Calculate average sentiment scores for each ticker"""
    avg_sentiment = {}
    for ticker in sentiment_scores:
        scores = sentiment_scores[ticker]
        avg_score = sum(scores) / len(scores)
        avg_sentiment[ticker] = {
            'score': avg_score,
            'post_count': post_count[ticker],
            'posts': ticker_posts[ticker]
        }
    return avg_sentiment

# Function to create post history file if it doesn't exist
def create_post_history_file():
    """Create post history file if it doesn't exist"""
    history_file = 'processed_posts.json'
    with open(history_file, 'w') as f:
        json.dump({"posts": [], "created_date": datetime.now(timezone.utc).isoformat()}, f)

# Function to check if a post ID is in history
def check_post_history(post_id):
    """Check if a post ID is already in the history"""
    history_file = 'processed_posts.json'
    with open(history_file, 'r') as f:
        data = json.load(f)
    return post_id in data.get("posts", [])

# Function to add a post ID to history
def add_post_to_history(post, score, ticker):
    """Add a post ID to the history"""
    history_file = 'processed_posts.json'
    with open(history_file, 'r') as f:
        data = json.load(f)
    if post.id not in data.get("posts", []):
        data["posts"].append({
            'post_id': post.id, 
            'ticker': ticker, 
            'score': round(score, 1), 
            'title': post.title[:100], 
            'date posted': datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()
            })
        data["last_modified"] = datetime.now(timezone.utc).isoformat()
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=4)