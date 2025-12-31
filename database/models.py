"""
Database connection helpers and path management.
"""
import os
import sqlite3
from contextlib import contextmanager


def get_db_path():
    """
    Returns the database path.
    Uses /data/scraper.db if /data exists (Render production),
    otherwise uses ./data/scraper.db (local development).
    """
    if os.path.exists('/data'):
        return '/data/scraper.db'

    # Ensure local data directory exists
    local_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(local_data_dir, exist_ok=True)
    return os.path.join(local_data_dir, 'scraper.db')


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Automatically handles connection opening and closing.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row):
    """Convert a sqlite3.Row to a dictionary."""
    if row is None:
        return None
    return dict(zip(row.keys(), row))
