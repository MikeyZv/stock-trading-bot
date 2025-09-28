import re
import json
from datetime import datetime, timezone


# Function to clean text for sentiment analysis
def clean_text(text):
    text = re.sub(r'http\S+', '', text)  # Replace URLs with empty string
    return text.strip() # Remove leading/trailing whitespace

# Function to create post history file if it doesn't exist
def create_post_history_file():
    """Create post history file if it doesn't exist"""
    history_file = 'processed_posts.json'
    with open(history_file, 'w') as f:
        json.dump({"posts": [], "created_date": datetime.now(timezone.utc).isoformat()}, f)

# Function to check if a post ID is in history - time complexity: O(n*m)
def check_post_history(post_id, file):
    """Check if a post ID is already in the history"""
    try:
        with open(file, 'r') as f:
            data = json.load(f)
        
        # Loop through each ticker in the JSON
        for ticker, ticker_data in data.items():
            # Get the posts array for this ticker
            posts = ticker_data.get("posts", [])
            
            # Check if post_id matches any post_id in this ticker's posts
            for post in posts:
                if post['post_id'] == post_id:
                    return True
        
        return False
        
    except (FileNotFoundError, json.JSONDecodeError):
        return False