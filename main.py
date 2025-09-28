from config import validate_env_vars
from sentiment import get_reddit_sentiment
# from trading import check_stock_exchange, execute_trades_based_on_sentiment, check_stock_price
# from utils import create_post_history_file
# from utils import check_post_history
# import json

def main():
    # Validate environment variables
    validate_env_vars()

    # print(check_post_history("1nql21w"))
    # Create post history file
    # create_post_history_file() 

    # # Get sentiment data
    get_reddit_sentiment('wallstreetbets', 20, "test.json")
    # with open('sentiment_output.json', 'w') as f:
    #     json.dump(sentiment_data, f, indent=4)
    
    # print("\nFinal sentiment data:")
    # print(json.dumps(sentiment, indent=2))
    
    # # Execute trades based on sentiment
    # execute_trades_based_on_sentiment(sentiment)
    # print(check_stock_price('RYCEY'))
    # print(check_stock_exchange('RYCEY'))

if __name__ == "__main__":
    main()