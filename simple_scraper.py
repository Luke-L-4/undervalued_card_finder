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
    """Set up SQLite database with proper schema"""
    conn = sqlite3.connect('card_prices.db')
    cursor = conn.cursor()
    
    # Create table with proper column types
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT NOT NULL,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            sale_date TEXT,  # Allow NULL sale dates
            listing_url TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    logger.info("Database setup completed successfully")
    return conn

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
    """Scrape eBay for Victor Wembanyama #136 Silver Prizm RC PSA 10 sales"""
    print("Starting scraper...")
    # Set up the request
    url = "https://www.ebay.com/sch/i.html?_nkw=victor+webanyama+prizm+%23136+silver+prizm+psa+10+rc&_sacat=0&_from=R40&_trksid=m570.l1313&_odkw=victor+webanyama+prizm+%23+136+silver+prizm+psa+10+rc&_osacat=0&LH_Complete=1&LH_Sold=1"
    print(f"Search URL: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1'
    }

    try:
        # Make the request
        print("Making request to eBay...")
        logger.info("Fetching eBay sales data...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Response status code: {response.status_code}")
        logger.info(f"Response status code: {response.status_code}")

        # Parse the HTML
        print("Parsing HTML response...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all sold items using the correct selector
        items = soup.select('li.s-item')
        print(f"Found {len(items)} items")
        logger.info(f"Found {len(items)} items")

        # Connect to database
        conn = sqlite3.connect('card_prices.db')
        cursor = conn.cursor()
        
        # Process each item
        for item in items:
            try:
                # Get title
                title_elem = item.select_one('div.s-item__title')
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                print(f"Processing item: {title}")

                # Get price
                price_elem = item.select_one('span.s-item__price')
                if not price_elem:
                    continue
                price_text = price_elem.text.strip()
                price = float(price_text.replace('$', '').replace(',', ''))
                print(f"Price: ${price}")

                # Get sale date
                date_elem = item.select_one('span.s-item__caption--signal')
                sale_date = None
                if date_elem:
                    date_text = date_elem.text.strip()
                    if 'Sold' in date_text:
                        # Extract the date part after "Sold"
                        date_text = date_text.replace('Sold', '').strip()
                        try:
                            # Parse the date (format: "MMM DD, YYYY")
                            parsed_date = datetime.strptime(date_text, '%b %d, %Y')
                            sale_date = parsed_date
                            print(f"Parsed sale date: {sale_date}")
                        except ValueError as e:
                            print(f"Could not parse date '{date_text}': {str(e)}")
                print(f"Sale date: {sale_date}")

                # Skip items without a sale date
                if not sale_date:
                    print(f"Skipping item: No sale date found - {title}")
                    continue

                # Get listing URL
                link_elem = item.select_one('a.s-item__link')
                listing_url = link_elem['href'] if link_elem else None
                print(f"URL: {listing_url}")

                # Skip items without a URL
                if not listing_url:
                    print(f"Skipping item: No URL found - {title}")
                    continue

                # Add to database
                cursor.execute('''
                    INSERT INTO card_prices 
                    (card_name, title, price, sale_date, listing_url, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'victor wembanyama prizm #136 silver prizm psa 10 rc',
                    title,
                    price,
                    sale_date.strftime('%Y-%m-%d'),
                    listing_url,
                    datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                ))
                print(f"Added to database: {title}")

            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")
                print(f"Error processing item: {str(e)}")
                continue

        # Commit changes
        conn.commit()
        conn.close()
        print(f"Finished processing sales data. Processed {len(items)} items.")
        logger.info(f"Finished processing sales data. Processed {len(items)} items.")

    except Exception as e:
        logger.error(f"Error fetching eBay data: {str(e)}")
        print(f"Error fetching eBay data: {str(e)}")
        raise

if __name__ == "__main__":
    get_ebay_sales() 