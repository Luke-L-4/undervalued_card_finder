import os
from dotenv import load_dotenv

load_dotenv()

# eBay API Configuration
EBAY_APP_ID = os.getenv('EBAY_APP_ID')
EBAY_CERT_ID = os.getenv('EBAY_CERT_ID')
EBAY_DEV_ID = os.getenv('EBAY_DEV_ID')

# Card Configuration
TRACKED_CARDS = [
    "luke doncic prizm rookie psa 10",
    # Add more cards here
]

# API Configuration
BATCH_SIZE = 5
API_CALL_INTERVAL = 3600  # 1 hour in seconds 