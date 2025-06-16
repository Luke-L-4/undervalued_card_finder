from ebaysdk.finding import Connection
from datetime import datetime
import pandas as pd
import sqlite3
import config
import time
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CardDataPipeline:
    def __init__(self):
        self.api = Connection(
            appid=config.EBAY_APP_ID,
            config_file=None,
            debug=True
        )
        self.conn = sqlite3.connect('card_prices.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                listing_url TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                condition TEXT,
                psa_grade INTEGER
            )
        ''')
        self.conn.commit()

    def extract_psa_grade(self, title):
        # Common patterns for PSA grades in titles
        patterns = [
            r'PSA\s*(\d+)',  # Matches "PSA 10" or "PSA10"
            r'PSA\s*Grade\s*(\d+)',  # Matches "PSA Grade 10"
            r'PSA\s*Graded\s*(\d+)',  # Matches "PSA Graded 10"
            r'PSA\s*(\d+)\s*Grade'  # Matches "PSA 10 Grade"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def fetch_ebay_data(self, card_name):
        try:
            response = self.api.execute('findItemsAdvanced', {
                'keywords': card_name,
                'itemFilter': [
                    {'name': 'ListingType', 'value': 'FixedPrice'},
                    {'name': 'Condition', 'value': '3000'},  # New condition
                ],
                'sortOrder': 'PricePlusShippingLowest'
            })

            if response.reply.ack == 'Success':
                items = response.reply.searchResult._count
                if items == '0':
                    return None

                results = []
                for item in response.reply.searchResult.item:
                    title = item.title
                    psa_grade = self.extract_psa_grade(title)
                    
                    results.append({
                        'card_name': card_name,
                        'title': title,
                        'price': float(item.sellingStatus.currentPrice.value),
                        'currency': item.sellingStatus.currentPrice._currencyId,
                        'listing_url': item.viewItemURL,
                        'timestamp': datetime.utcnow(),
                        'condition': item.condition.conditionDisplayName if hasattr(item, 'condition') else 'Unknown',
                        'psa_grade': psa_grade
                    })
                return results
            return None
        except Exception as e:
            logger.error(f"Error fetching data for {card_name}: {str(e)}")
            return None

    def process_batch(self):
        for card in config.TRACKED_CARDS:
            data = self.fetch_ebay_data(card)
            if data:
                cursor = self.conn.cursor()
                for item in data:
                    cursor.execute('''
                        INSERT INTO card_prices 
                        (card_name, title, price, currency, listing_url, timestamp, condition, psa_grade)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item['card_name'],
                        item['title'],
                        item['price'],
                        item['currency'],
                        item['listing_url'],
                        item['timestamp'],
                        item['condition'],
                        item['psa_grade']
                    ))
                self.conn.commit()
            time.sleep(1)  # Rate limiting

    def get_price_history(self, card_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT price, timestamp, psa_grade
            FROM card_prices
            WHERE card_name = ?
            ORDER BY timestamp ASC
        ''', (card_name,))
        return [{'price': row[0], 'timestamp': row[1], 'psa_grade': row[2]} for row in cursor.fetchall()]

    def get_latest_prices(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT card_name, price, timestamp, psa_grade
            FROM card_prices
            WHERE (card_name, timestamp) IN (
                SELECT card_name, MAX(timestamp)
                FROM card_prices
                GROUP BY card_name
            )
        ''')
        return [{
            '_id': row[0],
            'latest_price': row[1],
            'timestamp': row[2],
            'psa_grade': row[3]
        } for row in cursor.fetchall()]

    def __del__(self):
        self.conn.close() 