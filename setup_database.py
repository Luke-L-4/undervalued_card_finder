import sqlite3
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_database():
    """Create and set up the database with proper schema"""
    try:
        # Connect to database (this will create it if it doesn't exist)
        conn = sqlite3.connect('card_prices.db')
        cursor = conn.cursor()
        
        # Drop existing table if it exists
        cursor.execute('DROP TABLE IF EXISTS card_prices')
        
        # Create new table with proper schema
        cursor.execute('''
            CREATE TABLE card_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                sale_date TEXT NOT NULL,
                listing_url TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Create indexes for common queries
        cursor.execute('CREATE INDEX idx_sale_date ON card_prices(sale_date)')
        cursor.execute('CREATE INDEX idx_price ON card_prices(price)')
        
        conn.commit()
        logger.info("Database setup completed successfully")
        
        # Verify the table structure
        cursor.execute("PRAGMA table_info(card_prices)")
        columns = cursor.fetchall()
        print("\nDatabase structure:")
        print("=" * 50)
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, Not Null: {col[3]}")
        print("=" * 50)
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error setting up database: {str(e)}")
        return False

if __name__ == "__main__":
    setup_database() 