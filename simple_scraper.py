import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime, timedelta
import time
import random
import logging
import re
import sys

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_database():
    """Create the database and table if they don't exist"""
    try:
        conn = sqlite3.connect('card_prices.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                sale_date TEXT,
                listing_url TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        conn.commit()
        logger.info("Database setup completed successfully")
        return conn
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        raise

def is_within_six_months(date_text):
    """Check if the sale date is within the last 6 months"""
    try:
        now = datetime.now()
        six_months_ago = now - timedelta(days=180)  # Approximately 6 months
        
        # Extract number and unit from date text (e.g., "2 months ago" -> (2, "months"))
        match = re.match(r'(\d+)\s+(\w+)', date_text.lower())
        if not match:
            logger.warning(f"Could not parse date format: {date_text}")
            return False
            
        number = int(match.group(1))
        unit = match.group(2)
        
        # Convert to days
        if 'day' in unit:
            days_ago = number
        elif 'week' in unit:
            days_ago = number * 7
        elif 'month' in unit:
            days_ago = number * 30
        elif 'year' in unit:
            days_ago = number * 365
        else:
            logger.warning(f"Unknown time unit in date: {unit}")
            return False
            
        # Check if within last 180 days (6 months)
        is_within = days_ago <= 180
        logger.debug(f"Date {date_text} is {'within' if is_within else 'outside'} 6 month window")
        return is_within
    except Exception as e:
        logger.error(f"Error processing date {date_text}: {str(e)}")
        return False

def get_ebay_sales():
    """Scrape eBay for Luka Doncic PSA 10 sales"""
    # Set up the request
    url = "https://www.ebay.com/sch/i.html?_nkw=luka+doncic+prizm+rookie+psa+10&_sacat=0&LH_Complete=1&LH_Sold=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    try:
        # Make the request
        logger.info("Fetching eBay sales data...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"Response status code: {response.status_code}")

        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all sold items
        items = soup.find_all('div', {'class': 's-item__info'})
        logger.info(f"Found {len(items)} items")

        # Print raw HTML of the first item for inspection
        if items:
            print("Raw HTML of the first item:")
            print(items[0])

        # Process each item
        conn = setup_database()
        cursor = conn.cursor()
        items_processed = 0
        items_added = 0
        
        for item in items:
            try:
                # Get title
                title_elem = item.find('div', {'class': 's-item__title'})
                if not title_elem:
                    logger.debug("Skipping item: No title found")
                    print("Skipping item: No title found")
                    continue
                title = title_elem.text.strip()
                logger.debug(f"Processing item: {title}")
                
                # Skip if not PSA 10
                if not re.search(r'PSA\s*10!?', title.upper()):
                    logger.debug(f"Skipping item: Not PSA 10 - {title}")
                    print(f"Skipping item: Not PSA 10 - {title}")
                    continue
                
                # Get price
                price_elem = item.find('span', {'class': 's-item__price'})
                if not price_elem:
                    logger.debug("Skipping item: No price found")
                    print(f"Skipping item: No price found - {title}")
                    continue
                price_text = price_elem.text.strip().replace('$', '').replace(',', '')
                try:
                    price = float(price_text)
                except ValueError:
                    logger.warning(f"Could not parse price: {price_text}")
                    print(f"Skipping item: Could not parse price - {title} - {price_text}")
                    continue
                
                # Get sale date
                date_elem = item.find('span', {'class': 's-item__caption--signal'})
                if not date_elem:
                    logger.debug("Skipping item: No date found")
                    print(f"Skipping item: No date found - {title}")
                    print(f"Raw HTML for date element: {item.find('span', {'class': 's-item__caption--signal'})}")
                    print(f"Raw HTML for entire item: {item}")
                    continue
                sale_date = date_elem.text.strip()
                # Strip 'Sold' prefix if present
                if sale_date.startswith('Sold'):
                    sale_date = sale_date.replace('Sold', '').strip()
                # Parse the date using datetime.strptime
                try:
                    parsed_date = datetime.strptime(sale_date, '%b %d, %Y')
                    sale_date = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Could not parse date format: {sale_date}")
                    print(f"Skipping item: Could not parse date - {title} - {sale_date}")
                    continue
                
                # Compare the parsed date with the current date
                now = datetime.now()
                six_months_ago = now - timedelta(days=180)
                if parsed_date < six_months_ago:
                    logger.info(f"Skipping item older than 6 months: {sale_date}")
                    print(f"Skipping item: Older than 6 months - {title} - {sale_date}")
                    continue
                
                # Get URL
                url_elem = item.find('a', {'class': 's-item__link'})
                if not url_elem:
                    logger.debug("Skipping item: No URL found")
                    print(f"Skipping item: No URL found - {title}")
                    continue
                listing_url = url_elem['href']
                
                # Store in database
                cursor.execute('''
                    INSERT INTO card_prices 
                    (card_name, title, price, sale_date, listing_url, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'luka doncic prizm rookie psa 10',
                    title,
                    price,
                    sale_date,
                    listing_url,
                    datetime.utcnow()
                ))
                
                items_added += 1
                logger.info(f"Added sale: {title} at ${price} on {sale_date}")
                print(f"Added sale: {title} at ${price} on {sale_date}")
                
            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")
                print(f"Error processing item: {str(e)}")
                continue
            finally:
                items_processed += 1
        
        conn.commit()
        conn.close()
        logger.info(f"Finished processing sales data. Processed {items_processed} items, added {items_added} items to database.")
        
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        get_ebay_sales()
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1) 