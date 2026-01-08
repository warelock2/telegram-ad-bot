"""
Database module for SQLite-based state persistence.

This module handles all interactions with the SQLite database to store and
retrieve the bot's operational state, such as the last post time and a
history of which ads have been posted recently.
"""

import sqlite3
import datetime
from logger import log

DB_PATH = "/app/data/bot_state.db"

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DB_PATH)
    # Enable WAL (Write-Ahead Logging) mode.
    # This is crucial for allowing concurrent reads and writes, preventing
    # the scheduler from reading a stale state of the database.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Initializes the database and creates tables if they don't exist.
    This should be called once on bot startup.
    """
    log.info("Initializing database...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Key-value store for general state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Tracks when ads were last posted
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posted_ads (
                    ad_filename TEXT PRIMARY KEY,
                    post_timestamp TEXT NOT NULL
                )
            """)

            # Tracks timestamps of all messages for activity checking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_log (
                    timestamp TEXT NOT NULL
                )
            """)
            # Add an index for faster queries and pruning
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_timestamp ON message_log (timestamp)
            """)
            
            conn.commit()
        log.info("Database initialized successfully.")
    except sqlite3.Error as e:
        log.error(f"Database initialization failed: {e}")
        raise

# --- State Management ---

def set_state(key: str, value: str):
    """Saves or updates a key-value pair in the state table."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        log.debug(f"Set state for key '{key}'.")
    except sqlite3.Error as e:
        log.error(f"Failed to set state for key '{key}': {e}")

def get_state(key: str, default: str = None) -> str:
    """Retrieves a value for a given key from the state table."""
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
            if row:
                log.debug(f"Retrieved state for key '{key}'.")
                return row['value']
    except sqlite3.Error as e:
        log.error(f"Failed to get state for key '{key}': {e}")
    log.debug(f"No state found for key '{key}', returning default.")
    return default

# --- Ad Post History ---

def record_posted_ad(ad_filename: str):
    """Records that an ad was posted by saving its filename and the current timestamp."""
    timestamp = datetime.datetime.utcnow().isoformat()
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO posted_ads (ad_filename, post_timestamp) VALUES (?, ?)", (ad_filename, timestamp))
            conn.commit()
        log.info(f"Recorded post for ad '{ad_filename}'.")
    except sqlite3.Error as e:
        log.error(f"Failed to record post for ad '{ad_filename}': {e}")

def get_recently_posted_ads(hours: int) -> list[str]:
    """Returns a list of ad filenames that have been posted within the last X hours."""
    if hours <= 0:
        return []
    since_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    try:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT ad_filename FROM posted_ads WHERE post_timestamp >= ?", (since_time.isoformat(),)).fetchall()
            filenames = [row['ad_filename'] for row in rows]
            log.debug(f"Found {len(filenames)} recently posted ads in the last {hours} hours.")
            return filenames
    except sqlite3.Error as e:
        log.error(f"Failed to retrieve recently posted ads: {e}")
        return []

# --- Activity Checking ---

def log_message_timestamp():
    """Inserts a new timestamp into the message_log table."""
    timestamp = datetime.datetime.utcnow().isoformat()
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO message_log (timestamp) VALUES (?)", (timestamp,))
            conn.commit()
        log.debug(f"Logged new message timestamp for activity check: {timestamp}")
    except sqlite3.Error as e:
        log.error(f"Failed to log message timestamp: {e}")

def count_recent_messages(minutes: int) -> int:
    """Counts how many messages have been logged in the last X minutes."""
    if minutes <= 0:
        return 0
    since_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM message_log WHERE timestamp >= ?", (since_time.isoformat(),)).fetchone()
            count = row[0] if row else 0
            log.debug(f"Found {count} messages in the last {minutes} minutes.")

            # If the count is zero, let's do a forensic check.
            if count == 0:
                log.debug("Count is zero. Dumping all timestamps for forensic analysis...")
                all_rows = conn.execute("SELECT timestamp FROM message_log ORDER BY timestamp DESC").fetchall()
                if not all_rows:
                    log.debug("Forensic check confirms message_log table is empty.")
                else:
                    logged_times = [r[0] for r in all_rows]
                    log.debug(f"Forensic check found {len(logged_times)} rows. First 5: {logged_times[:5]}")

            return count
    except sqlite3.Error as e:
        log.error(f"Failed to count recent messages: {e}")
        return 0

def prune_old_message_logs(hours: int = 24):
    """Deletes message log entries older than a specified number of hours."""
    log.debug(f"Pruning message logs older than {hours} hours.")
    since_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM message_log WHERE timestamp < ?", (since_time.isoformat(),))
            conn.commit()
            log.info(f"Pruned {cursor.rowcount} old message log entries.")
    except sqlite3.Error as e:
        log.error(f"Failed to prune old message logs: {e}")