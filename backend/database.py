import sqlite3
import os
from datetime import datetime

DB_FILE = "yantrai.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create cameras table (ID to Role mapping)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cameras (
            id TEXT PRIMARY KEY,
            role TEXT
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT,
            timestamp DATETIME,
            description TEXT
        )
    ''')

    # Create config table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Set default values
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('logging_interval', '15')")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('video_source', '0')")
    
    conn.commit()
    conn.close()

def get_camera_role(camera_id: str, default_role: str) -> str:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT role FROM cameras WHERE id = ?", (camera_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return default_role

def update_camera_role(camera_id: str, new_role: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO cameras (id, role)
        VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET role = ?
    ''', (camera_id, new_role, new_role))
    
    conn.commit()
    conn.close()
    
def insert_log(camera_id: str, description: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO logs (camera_id, timestamp, description)
        VALUES (?, ?, ?)
    ''', (camera_id, datetime.now(), description))
    
    conn.commit()
    conn.close()

def get_config(key: str, default_value: str) -> str:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default_value

def update_config(key: str, value: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO config (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = ?
    ''', (key, value, value))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 10) -> list:
    """Fetch the most recent log entries for chat context."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT camera_id, timestamp, description
        FROM logs
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [{"camera_id": r[0], "timestamp": r[1], "description": r[2]} for r in rows]

# Initialize upon import
init_db()
