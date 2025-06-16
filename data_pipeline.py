from ebaysdk.finding import Connection
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
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
        self.mongo_client = MongoClient(config.MONGO_URI)
        self.db = self.mongo_client[config.MONGO_DB]
        self.collection = self.db.card_prices

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
                self.collection.insert_many(data)
            time.sleep(1)  # Rate limiting

    def get_price_history(self, card_name):
        pipeline = [
            {'$match': {'card_name': card_name}},
            {'$sort': {'timestamp': 1}},
            {'$project': {
                'price': 1,
                'timestamp': 1,
                'psa_grade': 1,
                '_id': 0
            }}
        ]
        return list(self.collection.aggregate(pipeline))

    def get_latest_prices(self):
        pipeline = [
            {'$sort': {'timestamp': -1}},
            {'$group': {
                '_id': '$card_name',
                'latest_price': {'$first': '$price'},
                'timestamp': {'$first': '$timestamp'},
                'psa_grade': {'$first': '$psa_grade'}
            }}
        ]
        return list(self.collection.aggregate(pipeline)) 