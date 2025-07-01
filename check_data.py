import sqlite3

def check_database():
    conn = sqlite3.connect('card_prices.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM card_prices')
    total_count = cursor.fetchone()[0]
    print(f"Total records in database: {total_count}")
    
    cursor.execute('''
        SELECT card_name, price, sale_date, listing_url
        FROM card_prices
        WHERE card_name LIKE '%wembanyama%'
        ORDER BY sale_date DESC
    ''')
    wemby_data = cursor.fetchall()
    
    print("\nVictor Wembanyama records:")
    print("=" * 50)
    for record in wemby_data:
        print(f"Card: {record[0]}")
        print(f"Price: ${record[1]}")
        print(f"Date: {record[2]}")
        print(f"URL: {record[3]}")
        print("-" * 30)
    
    conn.close()

if __name__ == "__main__":
    check_database() 