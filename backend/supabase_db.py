"""
supabase_db.py — PostgreSQL/Supabase database layer.
Replaces SQLite + in-memory state with persistent Supabase storage.
"""

import psycopg2
import psycopg2.extras
import os
import time
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    """Get a PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_tables():
    """Create tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            site_id TEXT UNIQUE,
            site_name TEXT NOT NULL,
            local_rtsp TEXT,
            remote_url TEXT,
            status TEXT DEFAULT 'active',
            registered_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS camera_roles (
            camera_id TEXT PRIMARY KEY,
            instruction TEXT,
            updated_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            camera_id TEXT NOT NULL,
            description TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT now()
        );
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("LOG: Supabase tables initialized.")


# --- Config ---
def get_config(key: str, default: str = "") -> str:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = %s", (key,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else default
    except Exception as e:
        print(f"LOG: DB get_config error: {e}")
        return default


def update_config(key: str, value: str):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO config (key, value, updated_at) VALUES (%s, %s, now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """, (key, value))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"LOG: DB update_config error: {e}")


# --- Camera Roles ---
def get_camera_role(camera_id: str, default: str = "") -> str:
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT instruction FROM camera_roles WHERE camera_id = %s", (camera_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else default
    except Exception as e:
        print(f"LOG: DB get_camera_role error: {e}")
        return default


def update_camera_role(camera_id: str, instruction: str):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO camera_roles (camera_id, instruction, updated_at) VALUES (%s, %s, now())
            ON CONFLICT (camera_id) DO UPDATE SET instruction = EXCLUDED.instruction, updated_at = now()
        """, (camera_id, instruction))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"LOG: DB update_camera_role error: {e}")


# --- Sites (Remote Agents) ---
def register_site(site_name: str, local_rtsp: str, remote_url: str, site_id: str = None) -> dict:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # If no site_id, use site_name as fallback for uniqueness (legacy support)
        unique_key = site_id if site_id else site_name
        
        cur.execute("""
            INSERT INTO sites (site_id, site_name, local_rtsp, remote_url, updated_at) 
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (site_id) DO UPDATE 
            SET site_name = EXCLUDED.site_name,
                local_rtsp = EXCLUDED.local_rtsp, 
                remote_url = EXCLUDED.remote_url, 
                status = 'active',
                updated_at = now()
            RETURNING *
        """, (site_id, site_name, local_rtsp, remote_url))
        site = dict(cur.fetchone())
        conn.commit()
        cur.close()
        conn.close()
        return site
    except Exception as e:
        print(f"LOG: DB register_site error: {e}")
        return {}


def get_all_sites() -> list:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM sites ORDER BY registered_at DESC")
        sites = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return sites
    except Exception as e:
        print(f"LOG: DB get_all_sites error: {e}")
        return []


# --- Logs ---
def insert_log(camera_id: str, description: str):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs (camera_id, description, timestamp) 
            VALUES (%s, %s, now())
        """, (camera_id, description))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"LOG: DB insert_log error: {e}")


def get_recent_logs(limit: int = 10) -> list:
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT camera_id, description, TO_CHAR(timestamp, 'HH24:MI:SS') as timestamp
            FROM logs 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (limit,))
        logs = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return logs
    except Exception as e:
        print(f"LOG: DB get_recent_logs error: {e}")
        return []
