import sqlite3

def get_all_sales():
    conn = sqlite3.connect('card_prices.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM card_sales')
    results = cursor.fetchall()
    conn.close()
    return results 