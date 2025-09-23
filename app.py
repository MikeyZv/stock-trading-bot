from flask import Flask, jsonify, render_template
from flask_cors import CORS
from clients import trading_client
import json

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
    try:
        # Read sentiment data from processed_posts.json
        with open('processed_posts.json', 'r') as f:
            data = json.load(f)
        
        # Extract sentiment data from posts
        sentiment_data = {}
        
        for post in data.get('posts', []):
            ticker = post.get('ticker')
            score = post.get('score', 0)
            
            if ticker:
                if ticker not in sentiment_data:
                    sentiment_data[ticker] = {
                        'score': 0,
                        'post_count': 0,
                        'posts': []
                    }
                
                # Add post data
                sentiment_data[ticker]['posts'].append({
                    'title': post.get('title', ''),
                    'score': score,
                    'timestamp': post.get('timestamp', '')
                })
                
                # Update aggregated data
                sentiment_data[ticker]['post_count'] += 1
                current_total = sentiment_data[ticker]['score'] * (sentiment_data[ticker]['post_count'] - 1)
                sentiment_data[ticker]['score'] = (current_total + score) / sentiment_data[ticker]['post_count']
        
        return jsonify(sentiment_data)
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return jsonify({'error': 'Sentiment data not available'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)