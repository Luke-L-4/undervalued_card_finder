import sqlite3

def explain_database():
    """Explain the database structure and show what's in it"""
    conn = sqlite3.connect('card_prices.db')
    cursor = conn.cursor()
    
    print("DATABASE STRUCTURE EXPLANATION")
    print("=" * 50)
    
    # Show all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n1. TABLES ({len(tables)} found):")
    for table in tables:
        print(f"   - {table[0]}")
    
    # Show all indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    print(f"\n2. INDEXES ({len(indexes)} found):")
    for index in indexes:
        print(f"   - {index[0]}")
    
    # Show table structure
    print(f"\n3. TABLE STRUCTURE:")
    cursor.execute("PRAGMA table_info(card_prices)")
    columns = cursor.fetchall()
    print("   card_prices table columns:")
    for col in columns:
        print(f"     - {col[1]} ({col[2]}) - Primary Key: {col[5]}, Not Null: {col[3]}")
    
    # Show index details
    print(f"\n4. INDEX DETAILS:")
    cursor.execute("PRAGMA index_list(card_prices)")
    index_list = cursor.fetchall()
    for idx in index_list:
        index_name = idx[1]
        cursor.execute(f"PRAGMA index_info({index_name})")
        index_info = cursor.fetchall()
        print(f"   - {index_name}: indexes column {index_info[0][2]}")
    
    # Show sample data
    print(f"\n5. SAMPLE DATA:")
    cursor.execute("SELECT COUNT(*) FROM card_prices")
    count = cursor.fetchone()[0]
    print(f"   Total records: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM card_prices LIMIT 3")
        sample_data = cursor.fetchall()
        print("   Sample records:")
        for i, record in enumerate(sample_data, 1):
            print(f"     Record {i}: ID={record[0]}, Card={record[1][:50]}..., Price=${record[3]}")
    
    conn.close()

if __name__ == "__main__":
    explain_database() 