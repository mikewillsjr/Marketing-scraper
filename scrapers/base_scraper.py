"""
Base scraper utilities shared by all scrapers.
"""
import os
import sqlite3
import time
from datetime import datetime
from functools import wraps


def get_db_path():
    """
    Returns the database path.
    Uses /data/scraper.db if /data exists (Render production),
    otherwise uses ./data/scraper.db (local development).
    """
    if os.path.exists('/data'):
        return '/data/scraper.db'

    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, 'data', 'scraper.db')


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def update_heartbeat(scraper_name, success=True, error=None, posts_found=0):
    """
    Update the heartbeat for a scraper.

    Args:
        scraper_name: Name of the scraper (e.g., 'reddit', 'twitter')
        success: Whether the scrape was successful
        error: Error message if failed
        posts_found: Number of posts found
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if success:
            cursor.execute('''
                INSERT INTO heartbeats (scraper_name, last_success, posts_found)
                VALUES (?, ?, ?)
                ON CONFLICT(scraper_name) DO UPDATE SET
                    last_success = excluded.last_success,
                    last_error = NULL,
                    posts_found = excluded.posts_found
            ''', (scraper_name, datetime.now().isoformat(), posts_found))
        else:
            cursor.execute('''
                INSERT INTO heartbeats (scraper_name, last_error)
                VALUES (?, ?)
                ON CONFLICT(scraper_name) DO UPDATE SET
                    last_error = excluded.last_error
            ''', (scraper_name, str(error) if error else 'Unknown error'))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to update heartbeat: {e}")


def retry_with_backoff(func=None, max_retries=3, base_delay=5):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        func: Function to wrap
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles each retry)
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
            raise last_exception
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def get_all_keywords():
    """
    Get all active keywords from all active businesses.

    Returns:
        List of keyword strings
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT k.keyword
            FROM keywords k
            JOIN businesses b ON k.business_id = b.id
            WHERE k.is_active = 1 AND b.is_active = 1
        ''')
        keywords = [row['keyword'] for row in cursor.fetchall()]
        conn.close()
        return keywords
    except Exception as e:
        print(f"Failed to get keywords: {e}")
        return []


def get_businesses_with_keywords():
    """
    Get all active businesses with their keywords.

    Returns:
        Dict of {business_id: {"name": name, "slug": slug, "keywords": [list]}}
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get businesses
        cursor.execute('''
            SELECT id, name, slug, domain, description
            FROM businesses
            WHERE is_active = 1
        ''')
        businesses = {}
        for row in cursor.fetchall():
            businesses[row['id']] = {
                'name': row['name'],
                'slug': row['slug'],
                'domain': row['domain'],
                'description': row['description'],
                'keywords': []
            }

        # Get keywords for each business
        cursor.execute('''
            SELECT business_id, keyword
            FROM keywords
            WHERE is_active = 1
        ''')
        for row in cursor.fetchall():
            if row['business_id'] in businesses:
                businesses[row['business_id']]['keywords'].append(row['keyword'])

        conn.close()
        return businesses
    except Exception as e:
        print(f"Failed to get businesses with keywords: {e}")
        return {}


def post_exists(source_id):
    """Check if a post with this source_id already exists."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM posts WHERE source_id = ?', (source_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        print(f"Failed to check post existence: {e}")
        return False


def insert_post(source, source_id, url, title, body, author, subreddit=None, created_at=None):
    """
    Insert a new post into the database.

    Returns:
        True if inserted, False if duplicate or error
    """
    if post_exists(source_id):
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO posts (source, source_id, url, title, body, author, subreddit, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source, source_id, url, title, body, author, subreddit, created_at))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Duplicate source_id
        return False
    except Exception as e:
        print(f"Failed to insert post: {e}")
        return False
