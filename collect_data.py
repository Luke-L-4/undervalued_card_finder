import schedule
import time
from data_pipeline import CardDataPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def collect_data():
    logger.info("Starting data collection...")
    pipeline = CardDataPipeline()
    pipeline.process_batch()
    logger.info("Data collection completed")

def main():
    # Run immediately on startup
    collect_data()
    
    # Schedule to run every hour
    schedule.every(1).hours.do(collect_data)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 