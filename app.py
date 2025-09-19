from flask import Flask, jsonify, render_template
from flask_cors import CORS
from trading_bot import trading_client, get_reddit_sentiment

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/account')
def get_account():
    account = trading_client.get_account()
    return jsonify({
        'portfolio_value': float(account.portfolio_value),
        'buying_power': float(account.buying_power),
        'cash': float(account.cash),
        'day_trade_buying_power': float(account.daytrading_buying_power),
        'pattern_day_trader': account.pattern_day_trader,
        'trading_blocked': account.trading_blocked,
        'account_blocked': account.account_blocked,
        'created_at': account.created_at
    })

@app.route('/api/positions')
def get_positions():
    positions = trading_client.get_all_positions()
    return jsonify([{
        'symbol': pos.symbol,
        'qty': float(pos.qty),
        'market_value': float(pos.market_value),
        'unrealized_pl': float(pos.unrealized_pl),
        'unrealized_plpc': float(pos.unrealized_plpc)
    } for pos in positions])

@app.route('/api/sentiment')
def get_sentiment():
    # Run your sentiment analysis
    sentiment = get_reddit_sentiment('wallstreetbets', 24, 10)
    return jsonify(sentiment)

if __name__ == '__main__':
    app.run(debug=True, port=5000)