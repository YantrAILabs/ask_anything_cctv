import sqlite3

def check_db():
    try:
        conn = sqlite3.connect("yantrai.db")
        cursor = conn.cursor()
        print("Latest 5 Logs:")
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
            
        print("\nCamera Roles:")
        cursor.execute("SELECT * FROM cameras")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    check_db()
