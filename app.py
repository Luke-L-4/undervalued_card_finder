from flask import Flask, render_template, jsonify
import plotly
import plotly.express as px
import json
from data_pipeline import CardDataPipeline
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
pipeline = CardDataPipeline()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/price-history/<card_name>')
def price_history(card_name):
    data = pipeline.get_price_history(card_name)
    df = pd.DataFrame(data)
    
    fig = px.line(df, x='timestamp', y='price',
                  title=f'Price History for {card_name}',
                  labels={'price': 'Price (USD)', 'timestamp': 'Date'})
    
    return jsonify(fig.to_dict())

@app.route('/api/latest-prices')
def latest_prices():
    data = pipeline.get_latest_prices()
    return jsonify(data)

@app.route('/api/cards')
def get_cards():
    return jsonify(pipeline.get_latest_prices())

if __name__ == '__main__':
    app.run(debug=True) 