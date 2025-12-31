#!/usr/bin/env python3
"""
Database initialization script.
Creates all required tables if they don't exist.
"""
import os
import sqlite3

def get_db_path():
    """Get the database path based on environment."""
    if os.path.exists('/data'):
        return '/data/scraper.db'

    # Ensure local data directory exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_data_dir = os.path.join(script_dir, 'data')
    os.makedirs(local_data_dir, exist_ok=True)
    return os.path.join(local_data_dir, 'scraper.db')


def init_database():
    """Create all database tables."""
    db_path = get_db_path()
    print(f"Initializing database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Businesses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            domain TEXT,
            description TEXT,
            spec_text TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Keywords table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            category TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        )
    ''')

    # Posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT UNIQUE NOT NULL,
            url TEXT,
            title TEXT,
            body TEXT,
            author TEXT,
            subreddit TEXT,
            created_at DATETIME,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Analysis table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            business_id INTEGER NOT NULL,
            relevance_score INTEGER,
            post_type TEXT,
            pain_score INTEGER,
            urgency TEXT,
            keywords_matched TEXT,
            competitor_mentioned TEXT,
            suggested_response TEXT,
            status TEXT DEFAULT 'new',
            analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        )
    ''')

    # Heartbeats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraper_name TEXT UNIQUE NOT NULL,
            last_success DATETIME,
            last_error TEXT,
            posts_found INTEGER DEFAULT 0
        )
    ''')

    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_source_id ON posts(source_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_post_id ON analysis(post_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_business_id ON analysis(business_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_status ON analysis(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords_business_id ON keywords(business_id)')

    conn.commit()
    conn.close()

    print("Database initialized successfully!")
    print("Tables created: businesses, keywords, posts, analysis, heartbeats")


if __name__ == '__main__':
    init_database()
