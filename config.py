import os
from dotenv import load_dotenv

load_dotenv()

# eBay API Configuration
EBAY_APP_ID = os.getenv('EBAY_APP_ID')
EBAY_CERT_ID = os.getenv('EBAY_CERT_ID')
EBAY_DEV_ID = os.getenv('EBAY_DEV_ID')
EBAY_AUTH_TOKEN = os.getenv('EBAY_AUTH_TOKEN')

# Card Configuration
TRACKED_CARDS = [
    "luka doncic prizm rookie psa 10",
    # Add more cards here if you wish :)
]

# API Configuration
BATCH_SIZE = 5
API_CALL_INTERVAL = 1  # 1 second between API calls (respects 5 calls/second limit)
MIN_RETRY_DELAY = 60   # 1 minute between retries if we hit rate limits
MAX_RETRIES = 3        # Maximum number of retry attempts

# Database Configuration
DATABASE_URL = 'sqlite:///card_prices.db'