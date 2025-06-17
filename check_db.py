import sqlite3

def check_database():
    try:
        # Connect to the database
        conn = sqlite3.connect('card_prices.db')
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_prices';")
        if not cursor.fetchone():
            print("The card_prices table does not exist yet.")
            return
            
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM card_prices;")
        count = cursor.fetchone()[0]
        print(f"Total records in database: {count}")
        
        # Show some sample data
        if count > 0:
            print("\nSample data:")
            cursor.execute("SELECT card_name, price, timestamp FROM card_prices LIMIT 5;")
            for row in cursor.fetchall():
                print(f"Card: {row[0]}, Price: ${row[1]}, Time: {row[2]}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database() 