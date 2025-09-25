import math
import requests
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from clients import trading_client
from config import ALPHA_VANTAGE_API_KEY
import time

# Returns trading account information
account = trading_client.get_account()

# Function to check stock prices 
def check_stock_price(ticker):
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
    r = requests.get(url)
    data = r.json()
    return float(data["Global Quote"]["05. price"]) if "Global Quote" in data else 0

# Function to allocate capital based on sentiment score
def allocate_capital_based_on_sentiment(avg_score, cash):
    """Allocate capital based on sentiment score"""
    if abs(avg_score) > 0.49 and abs(avg_score) < 0.65:
        return cash * 0.01
    elif abs(avg_score) > 0.65 and abs(avg_score) < 0.80:
        return cash * 0.03
    elif abs(avg_score) > 0.8:
        return cash * 0.06
    else:
        return 0

# Function to execute trades based on sentiment
def execute_trades_based_on_sentiment(sentiment_data):
    """Submit buy/sell orders via Alpaca based on average sentiment scores"""
    print("Executing trades based on sentiment...")
    
    for ticker, data in sentiment_data.items():
        avg_score = data['score']
        print(f"Evaluating {ticker}: avg_score = {avg_score}")

        cash = float(account.non_marginable_buying_power)
        price = check_stock_price(ticker)

        cash_allocated = allocate_capital_based_on_sentiment(avg_score, cash)

        if cash_allocated != 0:
            qty = math.floor(cash_allocated / price)
        
        print(cash_allocated)
        print(qty)
        print(price)
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