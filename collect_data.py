import schedule
import time
from data_pipeline import CardDataPipeline
import logging
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def collect_data():
    try:
        logger.info("Starting data collection...")
        pipeline = CardDataPipeline()
        pipeline.process_batch()
        logger.info("Data collection completed successfully")
    except Exception as e:
        logger.error(f"Error during data collection: {str(e)}")
        logger.info("Will retry at next scheduled interval")

def main():
    # Run immediately on startup
    collect_data()
    
    # Schedule to run every 2 hours (matching API_CALL_INTERVAL)
    schedule.every(config.API_CALL_INTERVAL).seconds.do(collect_data)
    
    logger.info(f"Data collection scheduled every {config.API_CALL_INTERVAL} seconds")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retrying if there's an error

if __name__ == "__main__":
    main() 