import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from datetime import datetime, timedelta
import sqlite3
import re
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EbayScraper:
    def __init__(self):
        """Initialize the scraper with necessary headers and database connection"""
        # Create a session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Rotate user agents
        self.ua = UserAgent()
        
        # Set up database
        self.conn = sqlite3.connect('card_prices.db')
        self.setup_database()
        
    def get_headers(self):
        """Generate random headers for each request"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
    def setup_database(self):
        """Set up the SQLite database with the required table"""
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
                psa_grade TEXT
            )
        ''')
        self.conn.commit()
        
    def extract_psa_grade(self, title):
        """Extract PSA grade from the title"""
        # Look for patterns like "PSA 10", "PSA10", "PSA-10"
        match = re.search(r'PSA[-\s]?(\d+)', title, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
        
    def get_completed_sales_url(self, card_name, page=1):
        """Generate eBay completed sales URL for a card"""
        # Format the search query
        search_query = card_name.replace(' ', '+')
        # Add filters for completed sales and PSA graded
        url = f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_sacat=0&LH_Complete=1&LH_Sold=1&_pgn={page}"
        return url
        
    def extract_price(self, price_text):
        """Extract price from text, handling ranges by taking the average"""
        try:
            # Remove currency symbol and commas
            price_text = price_text.replace('$', '').replace(',', '').strip()
            
            # Check if it's a price range
            if ' to ' in price_text:
                # Split the range and convert to floats
                min_price, max_price = map(float, price_text.split(' to '))
                # Return the average of the range
                return (min_price + max_price) / 2
            else:
                # Single price
                return float(price_text)
        except Exception as e:
            logger.error(f"Error extracting price from '{price_text}': {str(e)}")
            return None
        
    def scrape_card_sales(self, card_name, months_back=6):
        """Scrape completed sales for a card over the specified time period"""
        logger.info(f"Starting to scrape sales data for {card_name}")
        
        page = 1
        total_items = 0
        consecutive_errors = 0
        max_consecutive_errors = 3
        last_successful_page = 0
        
        while True:
            try:
                # Get the URL for the current page
                url = self.get_completed_sales_url(card_name, page)
                logger.info(f"Fetching page {page}: {url}")
                
                # Add random delay between requests (15-30 seconds)
                time.sleep(random.uniform(15, 30))
                
                # Make the request with rotating headers
                headers = self.get_headers()
                logger.info(f"Using User-Agent: {headers['User-Agent']}")
                
                response = self.session.get(url, headers=headers, timeout=30)
                
                # Check for 503 specifically
                if response.status_code == 503:
                    logger.error("Received 503 error. Taking a longer break...")
                    time.sleep(600)  # Wait 10 minutes
                    continue
                    
                response.raise_for_status()
                
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check if we're being blocked
                if "Robot Check" in response.text or "Security Measure" in response.text:
                    logger.error("eBay is blocking our requests. Waiting 10 minutes before retrying...")
                    time.sleep(600)  # Wait 10 minutes
                    continue
                
                # Find all sold items - try different selectors
                items = soup.find_all('div', {'class': 's-item__info'})
                if not items:
                    items = soup.find_all('div', {'class': 's-item'})
                if not items:
                    items = soup.find_all('li', {'class': 's-item'})
                
                if not items:
                    logger.warning(f"No items found on page {page}. HTML structure might have changed.")
                    logger.debug(f"Page content: {soup.prettify()[:1000]}")  # Log first 1000 chars of HTML
                    break
                    
                logger.info(f"Found {len(items)} potential items on page {page}")
                
                # Process each item
                items_processed = 0
                for item in items:
                    try:
                        # Extract title - try different selectors
                        title_elem = item.find('div', {'class': 's-item__title'})
                        if not title_elem:
                            title_elem = item.find('h3', {'class': 's-item__title'})
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        logger.debug(f"Processing item with title: {title}")
                        
                        # Skip if it's not a PSA graded card
                        if 'PSA' not in title.upper():
                            logger.debug(f"Skipping non-PSA card: {title}")
                            continue
                            
                        # Extract price - try different selectors
                        price_elem = item.find('span', {'class': 's-item__price'})
                        if not price_elem:
                            price_elem = item.find('div', {'class': 's-item__price'})
                        if not price_elem:
                            continue
                            
                        price_text = price_elem.text.strip()
                        price = self.extract_price(price_text)
                        
                        if price is None:
                            logger.debug(f"Could not extract price from: {price_text}")
                            continue
                        
                        # Extract date sold - try different selectors
                        date_elem = item.find('div', {'class': 's-item__title--tagblock'})
                        if not date_elem:
                            date_elem = item.find('div', {'class': 's-item__endedDate'})
                        if not date_elem:
                            continue
                            
                        date_text = date_elem.text.strip()
                        logger.debug(f"Found date: {date_text}")
                        
                        # Skip if the sale is too old
                        if 'month' in date_text.lower():
                            months = int(date_text.split()[0])
                            if months > months_back:
                                logger.debug(f"Skipping old sale from {months} months ago")
                                continue
                                
                        # Extract URL - try different selectors
                        url_elem = item.find('a', {'class': 's-item__link'})
                        if not url_elem:
                            url_elem = item.find('a', {'class': 's-item__title'})
                        if not url_elem:
                            continue
                            
                        listing_url = url_elem['href']
                        
                        # Extract PSA grade
                        psa_grade = self.extract_psa_grade(title)
                        
                        # Store in database
                        cursor = self.conn.cursor()
                        cursor.execute('''
                            INSERT INTO card_prices 
                            (card_name, title, price, currency, listing_url, timestamp, condition, psa_grade)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            card_name,
                            title,
                            price,
                            'USD',
                            listing_url,
                            datetime.utcnow(),
                            'Unknown',
                            psa_grade
                        ))
                        self.conn.commit()
                        
                        total_items += 1
                        items_processed += 1
                        consecutive_errors = 0  # Reset error counter on success
                        logger.info(f"Successfully processed item: {title} at ${price}")
                        
                    except Exception as e:
                        logger.error(f"Error processing item: {str(e)}")
                        continue
                
                if items_processed > 0:
                    last_successful_page = page
                    logger.info(f"Processed page {page}, total items so far: {total_items}")
                    page += 1
                else:
                    logger.warning(f"No valid items found on page {page}, might be blocked")
                    time.sleep(300)  # Wait 5 minutes
                
                # Add a longer delay between pages (30-45 seconds)
                time.sleep(random.uniform(30, 45))
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error scraping page {page}: {str(e)}")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors. Taking a longer break...")
                    time.sleep(900)  # Wait 15 minutes
                    consecutive_errors = 0
                    
                    # If we've had too many errors, go back to last successful page
                    if last_successful_page > 0:
                        page = last_successful_page + 1
                else:
                    time.sleep(300)  # Wait 5 minutes before retrying
                continue
                
        logger.info(f"Finished scraping {total_items} items for {card_name}")
        return total_items
        
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    # Example usage
    scraper = EbayScraper()
    try:
        # Scrape data for some example cards
        cards = [
            "luka doncic prizm rookie psa 10",
            "ja morant prizm rookie psa 10",
            "zion williamson prizm rookie psa 10"
        ]
        
        for card in cards:
            scraper.scrape_card_sales(card)
            # Add longer delay between cards (15-20 minutes)
            time.sleep(random.uniform(900, 1200))
            
    finally:
        scraper.close() 