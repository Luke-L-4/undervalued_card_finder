import sqlite3
import os

def test_database_creation():
    """Demonstrate how SQLite automatically creates database files"""
    
    # Test database name
    test_db = 'test_database.db'
    
    print("SQLite Database Creation Test")
    print("=" * 40)
    
    # Check if file exists before connection
    if os.path.exists(test_db):
        print(f"✓ Database file '{test_db}' already exists")
    else:
        print(f"✗ Database file '{test_db}' does not exist yet")
    
    # Connect to database (this will create it if it doesn't exist)
    print(f"\nConnecting to '{test_db}'...")
    conn = sqlite3.connect(test_db)
    print("✓ Connected successfully!")
    
    # Check if file exists after connection
    if os.path.exists(test_db):
        print(f"✓ Database file '{test_db}' now exists")
        file_size = os.path.getsize(test_db)
        print(f"  File size: {file_size} bytes")
    else:
        print(f"✗ Database file '{test_db}' still doesn't exist")
    
    # Create a simple table to show the database is working
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    ''')
    print("✓ Created test table")
    
    # Insert some data
    cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("Test Record",))
    print("✓ Inserted test data")
    
    # Query the data
    cursor.execute("SELECT * FROM test_table")
    result = cursor.fetchone()
    print(f"✓ Retrieved data: {result}")
    
    # Close connection
    conn.close()
    print("✓ Connection closed")
    
    # Clean up - remove test file
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"✓ Cleaned up test file '{test_db}'")
    
    print("\nKey Takeaway:")
    print("SQLite automatically creates the database file when you connect!")

if __name__ == "__main__":
    test_database_creation() 