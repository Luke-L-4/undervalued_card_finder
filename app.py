from flask import Flask, render_template, jsonify
import plotly
import plotly.express as px
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('card_prices.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/price-history/<card_name>')
def price_history(card_name):
    conn = get_db_connection()
    query = '''
    SELECT price, sale_date as timestamp
    FROM card_prices
    WHERE card_name = ?
    ORDER BY sale_date DESC
    '''
    data = conn.execute(query, (card_name,)).fetchall()
    conn.close()
    
    df = pd.DataFrame(data)
    if not df.empty:
        fig = px.line(df, x='timestamp', y='price',
                      title=f'Price History for {card_name}',
                      labels={'price': 'Price (USD)', 'timestamp': 'Date'})
        return jsonify(fig.to_dict())
    return jsonify({'error': 'No data found'})

@app.route('/api/latest-prices/<card_name>')
def latest_prices(card_name):
    conn = get_db_connection()
    query = '''
    SELECT card_name, price, sale_date, listing_url
    FROM card_prices
    WHERE card_name = ?
    ORDER BY sale_date DESC
    LIMIT 6
    '''
    data = conn.execute(query, (card_name,)).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in data])

@app.route('/api/sales-history/<card_name>')
def sales_history(card_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT card_name FROM card_prices')
    all_cards = [row[0] for row in cursor.fetchall()]
    
    search_pattern = f'%{card_name}%'
    
    query = '''
    SELECT card_name, price, sale_date, listing_url
    FROM card_prices
    WHERE card_name LIKE ?
    ORDER BY sale_date DESC
    '''
    data = cursor.execute(query, (search_pattern,)).fetchall()
    
    conn.close()
    return jsonify([dict(row) for row in data])

@app.route('/api/sales-history-no-outliers/<card_name>')
def sales_history_no_outliers(card_name):
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT card_name, price, sale_date, listing_url FROM card_prices WHERE card_name LIKE ? ORDER BY sale_date DESC",
        conn,
        params=(f'%{card_name}%',)
    )
    conn.close()
    if not df.empty:
        # Remove outliers using IQR
        Q1 = df['price'].quantile(0.25)
        Q3 = df['price'].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df = df[(df['price'] >= lower) & (df['price'] <= upper)]
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/cards')
def get_cards():
    conn = get_db_connection()
    query = '''
    SELECT DISTINCT card_name
    FROM card_prices
    ORDER BY card_name
    '''
    data = conn.execute(query).fetchall()
    conn.close()
    
    return jsonify([row['card_name'] for row in data])

if __name__ == '__main__':
    app.run(debug=True) 