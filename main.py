from config import validate_env_vars
from sentiment import get_reddit_sentiment
from trading import execute_trades_based_on_sentiment, check_stock_price
from utils import create_post_history_file
import json

def main():
    # Validate environment variables
    validate_env_vars()

    # Create post history file
    # create_post_history_file() 

    # # Get sentiment data
    # sentiment = get_reddit_sentiment('wallstreetbets', 72, 10)
    
    # print("\nFinal sentiment data:")
    # print(json.dumps(sentiment, indent=2))
    
    # # Execute trades based on sentiment
    # execute_trades_based_on_sentiment(sentiment)
    print(check_stock_price('DUOL'))

if __name__ == "__main__":
    main()