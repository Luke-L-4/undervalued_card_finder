from ebaysdk.finding import Connection
from datetime import datetime
import pandas as pd
import sqlite3
import config
import time
import logging
import re
import os
from dotenv import load_dotenv
import socket
import requests
from requests.exceptions import RequestException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CardDataPipeline:
    def __init__(self):
        """Initialize the data pipeline with eBay API connection"""
        try:
            # Initialize eBay API with proper configuration
            self.api = Connection(
                appid=config.EBAY_APP_ID,
                certid=config.EBAY_CERT_ID,
                devid=config.EBAY_DEV_ID,
                config_file=None,
                debug=True,
                domain='svcs.ebay.com',  # Changed to svcs.ebay.com for Finding API
                warnings=True,
                siteid='EBAY-US'
            )
            
            # Set up SQLite connection
            self.conn = sqlite3.connect('card_prices.db')
            self.setup_database()
            
            # Initialize rate limiting
            self.last_api_call = 0
            logger.info("CardDataPipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing CardDataPipeline: {str(e)}")
            raise

    def setup_database(self):
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

    def wait_for_rate_limit(self):
        """Wait for the appropriate time before making another API call"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        # Use a more conservative delay between calls (2 seconds)
        if time_since_last_call < 2:
            sleep_time = 2 - time_since_last_call
            logger.info(f"Rate limiting: Waiting {sleep_time:.2f} seconds before next API call")
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()

    def check_internet_connection(self):
        """Check if we have internet connectivity"""
        try:
            # Try to connect to a reliable server
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def fetch_ebay_data(self, card_name, max_retries=config.MAX_RETRIES, initial_delay=config.MIN_RETRY_DELAY):
        """Fetch data from eBay API with improved error handling and rate limiting"""
        retry_count = 0
        delay = initial_delay

        while retry_count < max_retries:
            try:
                # Check internet connection first
                if not self.check_internet_connection():
                    logger.error("No internet connection available")
                    time.sleep(delay)
                    retry_count += 1
                    continue

                # Wait for rate limit before making request
                self.wait_for_rate_limit()
                
                logger.info(f"Fetching data for card: {card_name} (Attempt {retry_count + 1}/{max_retries})")
                
                # Construct the API request
                request = {
                    'keywords': card_name,
                    'itemFilter': [
                        {'name': 'ListingType', 'value': 'FixedPrice'},
                        {'name': 'Condition', 'value': '3000'},  # New condition
                    ],
                    'sortOrder': 'PricePlusShippingLowest',
                    'paginationInput': {
                        'entriesPerPage': 100,
                        'pageNumber': 1
                    },
                    'outputSelector': ['SellerInfo', 'StoreInfo']
                }
                
                # Make the API call with explicit service name
                response = self.api.execute('findItemsAdvanced', request, {'service': 'FindingService'})

                if response.reply.ack == 'Success':
                    items = response.reply.searchResult._count
                    if items == '0':
                        logger.warning(f"No items found for {card_name}")
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
                    logger.info(f"Found {len(results)} items for {card_name}")
                    return results
                return None

            except (RequestException, socket.gaierror) as e:
                error_message = str(e)
                logger.error(f"Network error fetching data for {card_name}: {error_message}")
                
                if retry_count < max_retries - 1:
                    logger.info(f"Network error. Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    retry_count += 1
                    continue
                else:
                    logger.error(f"Max retries reached for {card_name}")
                    return None
                    
            except Exception as e:
                error_message = str(e)
                logger.error(f"Error fetching data for {card_name}: {error_message}")
                
                # Check if it's a rate limit error
                if "exceeded the number of times" in error_message or "errorId: 10001" in error_message:
                    if retry_count < max_retries - 1:
                        # Use a longer delay for rate limit errors (5 minutes)
                        wait_time = 300
                        logger.info(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    else:
                        logger.error(f"Max retries reached for {card_name}")
                        return None
                else:
                    # For other errors, return None immediately
                    return None

        return None

    def process_batch(self):
        """Process a batch of cards with rate limiting"""
        for card in config.TRACKED_CARDS:
            logger.info(f"Processing card: {card}")
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
                logger.info(f"Successfully processed {len(data)} listings for {card}")
            
            # Wait 1 second between cards to respect rate limits
            if card != config.TRACKED_CARDS[-1]:  # Don't wait after the last card
                logger.info(f"Waiting {config.API_CALL_INTERVAL} seconds before next card...")
                time.sleep(config.API_CALL_INTERVAL)

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