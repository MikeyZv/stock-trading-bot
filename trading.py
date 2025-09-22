import math
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.requests import StockLatestQuoteRequest
from clients import trading_client, stock_quote_client

# Returns trading account information
account = trading_client.get_account()

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

        if price == 0:
            price = 69.69  # Testing fallback price
        
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