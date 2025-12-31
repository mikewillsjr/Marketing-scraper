#!/usr/bin/env python3
"""
Mike's Scraper - Streamlit Dashboard
Main interface for managing businesses, viewing opportunities, and monitoring scrapers.
"""
import json
import os
import re
import sqlite3
import time
import traceback
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Initialize database on import
from init_db import init_database
init_database()

# Page config
st.set_page_config(
    page_title="Mike's Scraper",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Debug logging function - outputs to browser console
def log_to_console(message, data=None):
    """Log message to browser console via JavaScript."""
    if data is not None:
        try:
            data_str = json.dumps(data, default=str)
            js = f'console.log("[MIKES-SCRAPER] {message}:", {data_str});'
        except:
            js = f'console.log("[MIKES-SCRAPER] {message}:", "{str(data)}");'
    else:
        js = f'console.log("[MIKES-SCRAPER] {message}");'
    st.components.v1.html(f"<script>{js}</script>", height=0)

def log_error(message, error=None):
    """Log error to browser console."""
    error_str = str(error) if error else "Unknown error"
    tb = traceback.format_exc() if error else ""
    js = f'console.error("[MIKES-SCRAPER ERROR] {message}:", "{error_str}", "{tb}");'
    st.components.v1.html(f"<script>{js}</script>", height=0)

# Log startup
log_to_console("Dashboard loaded", {"db_path": os.path.exists('/data'), "timestamp": datetime.now().isoformat()})


# ============================================================================
# Database Helpers
# ============================================================================

def get_db_path():
    """Get the database path based on environment."""
    if os.path.exists('/data'):
        return '/data/scraper.db'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'data', 'scraper.db')


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def dict_from_row(row):
    """Convert sqlite3.Row to dict."""
    if row is None:
        return None
    return dict(zip(row.keys(), row))


# ============================================================================
# Data Fetching Functions
# ============================================================================

def get_stats():
    """Get dashboard statistics."""
    try:
        log_to_console("get_stats() called")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total posts
        cursor.execute('SELECT COUNT(*) as count FROM posts')
        total_posts = cursor.fetchone()['count']

        # Posts today
        today = datetime.now().date().isoformat()
        cursor.execute("SELECT COUNT(*) as count FROM posts WHERE DATE(scraped_at) = ?", (today,))
        posts_today = cursor.fetchone()['count']

        # High priority opportunities (relevance >= 7, status = 'new')
        cursor.execute("""
            SELECT COUNT(*) as count FROM analysis
            WHERE relevance_score >= 7 AND status = 'new'
        """)
        high_priority = cursor.fetchone()['count']

        # Posts by source
        cursor.execute("""
            SELECT source, COUNT(*) as count FROM posts
            GROUP BY source ORDER BY count DESC
        """)
        by_source = {row['source']: row['count'] for row in cursor.fetchall()}

        # Opportunities by business
        cursor.execute("""
            SELECT b.name, COUNT(*) as count
            FROM analysis a
            JOIN businesses b ON a.business_id = b.id
            WHERE a.relevance_score >= 7
            GROUP BY b.id ORDER BY count DESC
        """)
        by_business = {row['name']: row['count'] for row in cursor.fetchall()}

        conn.close()
        stats = {
            'total_posts': total_posts,
            'posts_today': posts_today,
            'high_priority': high_priority,
            'by_source': by_source,
            'by_business': by_business
        }
        log_to_console("get_stats() result", stats)
        return stats
    except Exception as e:
        log_error("get_stats() failed", e)
        raise


def get_opportunities(business_filter=None, status_filter=None, limit=50):
    """Get high-relevance opportunities."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT a.*, p.source, p.title, p.body, p.url, p.author, p.subreddit,
               p.created_at as post_date, b.name as business_name
        FROM analysis a
        JOIN posts p ON a.post_id = p.id
        JOIN businesses b ON a.business_id = b.id
        WHERE a.relevance_score >= 7
    """
    params = []

    if business_filter and business_filter != "All":
        query += " AND b.name = ?"
        params.append(business_filter)

    if status_filter and status_filter != "All":
        query += " AND a.status = ?"
        params.append(status_filter)

    query += " ORDER BY a.analyzed_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    opportunities = [dict_from_row(row) for row in cursor.fetchall()]
    conn.close()
    return opportunities


def get_all_posts(search_query=None, limit=50, offset=0):
    """Get all posts with optional search."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT * FROM posts
            WHERE title LIKE ? OR body LIKE ?
            ORDER BY scraped_at DESC
            LIMIT ? OFFSET ?
        """, (f'%{search_query}%', f'%{search_query}%', limit, offset))
    else:
        cursor.execute("""
            SELECT * FROM posts
            ORDER BY scraped_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

    posts = [dict_from_row(row) for row in cursor.fetchall()]

    # Get total count
    if search_query:
        cursor.execute("""
            SELECT COUNT(*) as count FROM posts
            WHERE title LIKE ? OR body LIKE ?
        """, (f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("SELECT COUNT(*) as count FROM posts")
    total = cursor.fetchone()['count']

    conn.close()
    return posts, total


def get_businesses():
    """Get all businesses with keyword counts."""
    try:
        log_to_console("get_businesses() called")
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT b.*, COUNT(k.id) as keyword_count
            FROM businesses b
            LEFT JOIN keywords k ON b.id = k.business_id AND k.is_active = 1
            GROUP BY b.id
            ORDER BY b.created_at DESC
        """)
        businesses = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        log_to_console("get_businesses() result", {"count": len(businesses), "businesses": businesses})
        return businesses
    except Exception as e:
        log_error("get_businesses() failed", e)
        raise


def get_business_keywords(business_id):
    """Get keywords for a business."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM keywords
        WHERE business_id = ?
        ORDER BY category, keyword
    """, (business_id,))
    keywords = [dict_from_row(row) for row in cursor.fetchall()]
    conn.close()
    return keywords


def get_business_names():
    """Get list of business names for filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM businesses WHERE is_active = 1 ORDER BY name")
    names = [row['name'] for row in cursor.fetchall()]
    conn.close()
    return names


def get_heartbeats():
    """Get scraper heartbeats."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM heartbeats ORDER BY scraper_name")
    heartbeats = [dict_from_row(row) for row in cursor.fetchall()]
    conn.close()
    return heartbeats


# ============================================================================
# Database Modification Functions
# ============================================================================

def create_slug(name):
    """Create a URL-safe slug from a business name."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug.strip('-')


def add_business(name, domain, description, spec_text, keywords):
    """Add a new business with keywords."""
    conn = get_db_connection()
    cursor = conn.cursor()

    slug = create_slug(name)

    # Check for duplicate slug
    cursor.execute("SELECT id FROM businesses WHERE slug = ?", (slug,))
    if cursor.fetchone():
        conn.close()
        return False, "A business with this name already exists"

    try:
        cursor.execute("""
            INSERT INTO businesses (name, slug, domain, description, spec_text)
            VALUES (?, ?, ?, ?, ?)
        """, (name, slug, domain, description, spec_text))

        business_id = cursor.lastrowid

        # Insert keywords
        for kw in keywords:
            cursor.execute("""
                INSERT INTO keywords (business_id, keyword, category)
                VALUES (?, ?, ?)
            """, (business_id, kw['keyword'], kw.get('category', 'direct')))

        conn.commit()
        conn.close()
        return True, "Business added successfully"

    except Exception as e:
        conn.close()
        return False, str(e)


def update_analysis_status(analysis_id, new_status):
    """Update the status of an analysis."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE analysis SET status = ? WHERE id = ?", (new_status, analysis_id))
    conn.commit()
    conn.close()


def toggle_business_active(business_id, is_active):
    """Toggle business active status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE businesses SET is_active = ? WHERE id = ?", (is_active, business_id))
    conn.commit()
    conn.close()


def delete_business(business_id):
    """Delete a business and its keywords."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keywords WHERE business_id = ?", (business_id,))
    cursor.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
    conn.commit()
    conn.close()


def add_keyword(business_id, keyword, category):
    """Add a keyword to a business."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO keywords (business_id, keyword, category)
        VALUES (?, ?, ?)
    """, (business_id, keyword, category))
    conn.commit()
    conn.close()


def toggle_keyword_active(keyword_id, is_active):
    """Toggle keyword active status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE keywords SET is_active = ? WHERE id = ?", (is_active, keyword_id))
    conn.commit()
    conn.close()


def delete_keyword(keyword_id):
    """Delete a keyword."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    conn.commit()
    conn.close()


# ============================================================================
# UI Components
# ============================================================================

MODEL_EMOJIS = {
    'gpt-4o': '🔵',
    'claude-opus-4.5': '🟠',
    'deepseek': '🟢',
    'gemini-2.5': '🔴'
}


def render_model_dots(models):
    """Render colored dots for models that suggested a keyword."""
    dots = []
    for model, emoji in MODEL_EMOJIS.items():
        if model in models:
            dots.append(emoji)
    return ''.join(dots)


def render_category_pill(category):
    """Render a category label."""
    colors = {
        'direct': '🎯',
        'pain_point': '😫',
        'question': '❓',
        'competitor': '🏢',
        'industry': '🏭'
    }
    return colors.get(category, '📌')


# ============================================================================
# Tab 1: Overview
# ============================================================================

def render_overview_tab():
    """Render the Overview tab."""
    log_to_console("render_overview_tab() called")
    stats = get_stats()

    # Check if there are any businesses
    businesses = get_businesses()
    log_to_console("render_overview_tab() businesses check", {"has_businesses": len(businesses) > 0, "count": len(businesses)})
    if not businesses:
        st.info("👋 **Welcome to Mike's Scraper!**\n\nAdd your first business in the **Businesses** tab to get started.")
        log_to_console("render_overview_tab() showing welcome message - no businesses")
        return

    log_to_console("render_overview_tab() showing metrics")
    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Posts Scraped", stats['total_posts'])
    with col2:
        st.metric("Posts Today", stats['posts_today'])
    with col3:
        st.metric("High-Priority Opportunities", stats['high_priority'])

    st.divider()

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Posts by Source")
        if stats['by_source']:
            df = pd.DataFrame(list(stats['by_source'].items()), columns=['Source', 'Count'])
            st.bar_chart(df.set_index('Source'))
        else:
            st.info("No posts yet - scrapers will run automatically")

    with col2:
        st.subheader("Opportunities by Business")
        if stats['by_business']:
            df = pd.DataFrame(list(stats['by_business'].items()), columns=['Business', 'Count'])
            st.bar_chart(df.set_index('Business'))
        else:
            st.info("No opportunities found yet")

    # Manual scraper controls
    st.divider()
    st.subheader("Run Scrapers")
    st.caption("Manually trigger scrapers to fetch posts now")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔴 Reddit", key="run_reddit"):
            with st.spinner("Scraping Reddit..."):
                try:
                    from scrapers.reddit_scraper import scrape_reddit
                    from scrapers.base_scraper import update_heartbeat
                    posts = scrape_reddit()
                    update_heartbeat('reddit', success=True, posts_found=posts)
                    st.success(f"Found {posts} new posts!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        if st.button("🟠 Hacker News", key="run_hn"):
            with st.spinner("Scraping Hacker News..."):
                try:
                    from scrapers.hackernews_scraper import scrape_hackernews
                    from scrapers.base_scraper import update_heartbeat
                    posts = scrape_hackernews()
                    update_heartbeat('hackernews', success=True, posts_found=posts)
                    st.success(f"Found {posts} new posts!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col3:
        if st.button("🟣 TikTok", key="run_tiktok"):
            with st.spinner("Scraping TikTok..."):
                try:
                    from scrapers.tiktok_scraper import scrape_tiktok
                    from scrapers.base_scraper import update_heartbeat
                    posts = scrape_tiktok()
                    update_heartbeat('tiktok', success=True, posts_found=posts)
                    st.success(f"Found {posts} new posts!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with col4:
        if st.button("🤖 Classify Posts", key="run_classify"):
            with st.spinner("Classifying posts..."):
                try:
                    from processing.classifier import classify_posts
                    from scrapers.base_scraper import update_heartbeat
                    count = classify_posts(batch_size=10)
                    update_heartbeat('classifier', success=True, posts_found=count)
                    st.success(f"Classified {count} posts!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================================
# Tab 2: Opportunities
# ============================================================================

def render_opportunities_tab():
    """Render the Opportunities tab."""
    st.subheader("High-Priority Opportunities")
    st.caption("Posts with relevance score >= 7")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        business_names = ["All"] + get_business_names()
        business_filter = st.selectbox("Filter by Business", business_names, key="opp_business")
    with col2:
        status_options = ["All", "new", "reviewed", "actioned", "ignored"]
        status_filter = st.selectbox("Filter by Status", status_options, key="opp_status")

    opportunities = get_opportunities(
        business_filter=business_filter if business_filter != "All" else None,
        status_filter=status_filter if status_filter != "All" else None
    )

    if not opportunities:
        st.info("No opportunities yet. Opportunities appear when posts are classified with relevance >= 7.")
        return

    for opp in opportunities:
        with st.expander(f"**{opp['source'].upper()}** | {opp['business_name']} | {(opp.get('title') or opp.get('body', ''))[:60]}..."):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**Title:** {opp.get('title') or 'N/A'}")
                st.write(f"**Body:** {opp.get('body') or 'N/A'}")
                if opp.get('url'):
                    st.write(f"**URL:** [{opp['url'][:50]}...]({opp['url']})")

            with col2:
                st.write(f"**Relevance:** {opp.get('relevance_score')}/10")
                st.write(f"**Urgency:** {opp.get('urgency')}")
                st.write(f"**Pain Score:** {opp.get('pain_score')}/10")
                st.write(f"**Type:** {opp.get('post_type')}")

            with col3:
                current_status = opp.get('status', 'new')
                new_status = st.selectbox(
                    "Status",
                    ["new", "reviewed", "actioned", "ignored"],
                    index=["new", "reviewed", "actioned", "ignored"].index(current_status),
                    key=f"status_{opp['id']}"
                )
                if new_status != current_status:
                    update_analysis_status(opp['id'], new_status)
                    st.rerun()

            if opp.get('suggested_response'):
                st.write("**Suggested Response:**")
                st.info(opp['suggested_response'])


# ============================================================================
# Tab 3: All Posts
# ============================================================================

def render_all_posts_tab():
    """Render the All Posts tab."""
    st.subheader("All Scraped Posts")

    # Search
    search = st.text_input("Search posts", placeholder="Search by title or body...")

    # Pagination
    page = st.number_input("Page", min_value=1, value=1, key="posts_page")
    per_page = 50
    offset = (page - 1) * per_page

    posts, total = get_all_posts(search_query=search if search else None, limit=per_page, offset=offset)

    if not posts:
        st.info("No posts yet - scrapers will run automatically")
        return

    st.write(f"Showing {offset + 1}-{min(offset + per_page, total)} of {total} posts")

    # Display as table
    df_data = []
    for post in posts:
        df_data.append({
            'Date': post['scraped_at'][:10] if post['scraped_at'] else 'N/A',
            'Source': post['source'],
            'Title': (post.get('title') or post.get('body', ''))[:80],
            'Author': post.get('author') or 'N/A'
        })

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)


# ============================================================================
# Tab 4: Businesses (Most Important!)
# ============================================================================

def render_businesses_tab():
    """Render the Businesses tab."""

    # Model color legend
    st.markdown("**Model Colors:** 🔵 GPT-5.2  🟠 Claude Opus 4.5  🔴 Gemini 3 Pro  🟢 DeepSeek V3.2")
    st.divider()

    # -------------------------------------------------------------------------
    # Add New Business Section
    # -------------------------------------------------------------------------
    st.subheader("Add New Business")

    with st.form("add_business_form"):
        name = st.text_input("Business Name *", placeholder="e.g., FileFluent")
        domain = st.text_input("Domain (optional)", placeholder="e.g., filefluent.com")
        description = st.text_area(
            "Description (optional)",
            placeholder="What does this business do? What problems does it solve?",
            height=100
        )
        spec_text = st.text_area(
            "Documents & Context (optional)",
            placeholder="Paste any specs, marketing copy, competitor research, etc.",
            height=150
        )

        generate_btn = st.form_submit_button("🔍 Generate Keyword Suggestions")

    # Handle keyword generation
    if generate_btn:
        if not name:
            st.error("Business name is required")
        elif not description and not spec_text:
            st.error("Please provide either a description or documents/context")
        else:
            with st.spinner("🤖 Asking 4 AI models for keyword suggestions..."):
                try:
                    from processing.keyword_suggester import suggest_keywords_sync
                    suggestions = suggest_keywords_sync(name, domain or '', description or '', spec_text or '')
                    st.session_state['keyword_suggestions'] = suggestions
                    st.session_state['new_business'] = {
                        'name': name,
                        'domain': domain,
                        'description': description,
                        'spec_text': spec_text
                    }
                except Exception as e:
                    st.error(f"Failed to generate suggestions: {e}")
                    st.session_state['keyword_suggestions'] = []

    # Display keyword suggestions if available
    if 'keyword_suggestions' in st.session_state and st.session_state['keyword_suggestions']:
        suggestions = st.session_state['keyword_suggestions']
        business_info = st.session_state.get('new_business', {})

        st.subheader(f"Keyword Suggestions for {business_info.get('name', 'New Business')}")

        # Group by category
        categories = {
            'direct': ('🎯 Direct Terms', []),
            'pain_point': ('😫 Pain Points', []),
            'question': ('❓ Questions', []),
            'competitor': ('🏢 Competitors', []),
            'industry': ('🏭 Industry Terms', [])
        }

        for kw in suggestions:
            cat = kw.get('category', 'direct')
            if cat in categories:
                categories[cat][1].append(kw)

        # Initialize selected keywords in session state
        if 'selected_keywords' not in st.session_state:
            st.session_state['selected_keywords'] = {}
            for kw in suggestions:
                # Pre-select if 2+ models suggested it
                st.session_state['selected_keywords'][kw['keyword']] = kw['model_count'] >= 2

        # Display by category
        for cat_key, (cat_label, cat_keywords) in categories.items():
            if cat_keywords:
                # Category header with Select All button
                col_header, col_btn = st.columns([3, 1])
                with col_header:
                    st.write(f"**{cat_label}** ({len(cat_keywords)} keywords)")
                with col_btn:
                    if st.button(f"Select All", key=f"select_all_{cat_key}"):
                        for kw in cat_keywords:
                            st.session_state['selected_keywords'][kw['keyword']] = True
                        st.rerun()

                for kw in cat_keywords:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        checked = st.checkbox(
                            f"{kw['keyword']} {render_model_dots(kw['models'])}",
                            value=st.session_state['selected_keywords'].get(kw['keyword'], False),
                            key=f"kw_{kw['keyword']}"
                        )
                        st.session_state['selected_keywords'][kw['keyword']] = checked
                    with col2:
                        st.caption(f"{kw['model_count']} models")

        st.divider()

        # Custom keyword input
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            custom_kw = st.text_input("Add custom keyword", key="custom_keyword")
        with col2:
            custom_cat = st.selectbox(
                "Category",
                ['direct', 'pain_point', 'question', 'competitor', 'industry'],
                key="custom_category"
            )
        with col3:
            if st.button("Add", key="add_custom"):
                if custom_kw:
                    suggestions.append({
                        'keyword': custom_kw,
                        'category': custom_cat,
                        'models': ['custom'],
                        'model_count': 1
                    })
                    st.session_state['keyword_suggestions'] = suggestions
                    st.session_state['selected_keywords'][custom_kw] = True
                    st.rerun()

        # Count selected
        selected_count = sum(1 for v in st.session_state['selected_keywords'].values() if v)
        st.write(f"**Selected: {selected_count} keywords**")

        # Save button
        if st.button("💾 Save Business & Keywords", type="primary"):
            selected_keywords = [
                {'keyword': kw['keyword'], 'category': kw['category']}
                for kw in suggestions
                if st.session_state['selected_keywords'].get(kw['keyword'], False)
            ]

            if not selected_keywords:
                st.error("Please select at least one keyword")
            else:
                success, msg = add_business(
                    business_info['name'],
                    business_info.get('domain'),
                    business_info.get('description'),
                    business_info.get('spec_text'),
                    selected_keywords
                )
                if success:
                    st.success(msg)
                    # Clear session state
                    del st.session_state['keyword_suggestions']
                    del st.session_state['selected_keywords']
                    del st.session_state['new_business']
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()

    # -------------------------------------------------------------------------
    # Existing Businesses Section
    # -------------------------------------------------------------------------
    st.subheader("Existing Businesses")

    businesses = get_businesses()

    if not businesses:
        st.info("No businesses yet. Add your first business above!")
        return

    for biz in businesses:
        with st.expander(f"**{biz['name']}** | {biz.get('domain') or 'No domain'} | {biz['keyword_count']} keywords"):
            col1, col2 = st.columns([3, 1])

            with col1:
                if biz.get('description'):
                    st.write(f"**Description:** {biz['description'][:200]}...")

                # Show keywords grouped by category
                keywords = get_business_keywords(biz['id'])
                if keywords:
                    st.write("**Keywords:**")

                    # Group by category
                    by_cat = {}
                    for kw in keywords:
                        cat = kw.get('category') or 'other'
                        if cat not in by_cat:
                            by_cat[cat] = []
                        by_cat[cat].append(kw)

                    for cat, kws in by_cat.items():
                        st.write(f"_{render_category_pill(cat)} {cat.replace('_', ' ').title()}_")
                        for kw in kws:
                            kcol1, kcol2, kcol3 = st.columns([3, 1, 1])
                            with kcol1:
                                st.write(kw['keyword'])
                            with kcol2:
                                active = st.checkbox(
                                    "Active",
                                    value=bool(kw['is_active']),
                                    key=f"kw_active_{kw['id']}"
                                )
                                if active != bool(kw['is_active']):
                                    toggle_keyword_active(kw['id'], active)
                                    st.rerun()
                            with kcol3:
                                if st.button("🗑️", key=f"del_kw_{kw['id']}"):
                                    delete_keyword(kw['id'])
                                    st.rerun()

            with col2:
                # Active toggle
                is_active = st.checkbox(
                    "Business Active",
                    value=bool(biz['is_active']),
                    key=f"biz_active_{biz['id']}"
                )
                if is_active != bool(biz['is_active']):
                    toggle_business_active(biz['id'], is_active)
                    st.rerun()

                # Delete button
                if st.button("🗑️ Delete Business", key=f"del_biz_{biz['id']}"):
                    st.session_state[f'confirm_delete_{biz["id"]}'] = True

                # Confirmation
                if st.session_state.get(f'confirm_delete_{biz["id"]}'):
                    st.warning("Are you sure?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes", key=f"yes_{biz['id']}"):
                            delete_business(biz['id'])
                            del st.session_state[f'confirm_delete_{biz["id"]}']
                            st.rerun()
                    with col_no:
                        if st.button("No", key=f"no_{biz['id']}"):
                            del st.session_state[f'confirm_delete_{biz["id"]}']
                            st.rerun()

            # Add keyword form
            st.write("---")
            kcol1, kcol2, kcol3 = st.columns([2, 1, 1])
            with kcol1:
                new_kw = st.text_input("New keyword", key=f"new_kw_{biz['id']}")
            with kcol2:
                new_cat = st.selectbox(
                    "Category",
                    ['direct', 'pain_point', 'question', 'competitor', 'industry'],
                    key=f"new_cat_{biz['id']}"
                )
            with kcol3:
                if st.button("Add Keyword", key=f"add_kw_{biz['id']}"):
                    if new_kw:
                        add_keyword(biz['id'], new_kw, new_cat)
                        st.rerun()


# ============================================================================
# Tab 5: Health
# ============================================================================

def render_health_tab():
    """Render the Health tab."""
    st.subheader("Scraper Health")

    heartbeats = get_heartbeats()
    expected_scrapers = ['reddit', 'twitter', 'hackernews', 'tiktok', 'instagram', 'classifier']
    heartbeat_map = {h['scraper_name']: h for h in heartbeats}

    cutoff = datetime.now() - timedelta(hours=24)

    for scraper in expected_scrapers:
        hb = heartbeat_map.get(scraper)

        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

        with col1:
            if hb and hb.get('last_success'):
                try:
                    last_success = datetime.fromisoformat(hb['last_success'])
                    if last_success > cutoff:
                        st.write("🟢")
                    else:
                        st.write("🔴")
                except:
                    st.write("⚪")
            else:
                st.write("⚪")

        with col2:
            st.write(f"**{scraper.title()}**")

        with col3:
            if hb:
                if hb.get('last_success'):
                    st.write(f"Last success: {hb['last_success'][:19]}")
                elif hb.get('last_error'):
                    st.write(f"Error: {hb['last_error'][:50]}")
                else:
                    st.write("Waiting for first run")
            else:
                st.write("Waiting for first run")

        with col4:
            if hb:
                st.write(f"{hb.get('posts_found', 0)} posts")


# ============================================================================
# Main App
# ============================================================================

def main():
    log_to_console("main() called - rendering dashboard")
    st.title("🔍 Mike's Scraper")

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🎯 Opportunities",
        "📝 All Posts",
        "🏢 Businesses",
        "💚 Health"
    ])

    with tab1:
        log_to_console("Tab 1 (Overview) rendering")
        render_overview_tab()

    with tab2:
        log_to_console("Tab 2 (Opportunities) rendering")
        render_opportunities_tab()

    with tab3:
        log_to_console("Tab 3 (All Posts) rendering")
        render_all_posts_tab()

    with tab4:
        log_to_console("Tab 4 (Businesses) rendering")
        render_businesses_tab()

    with tab5:
        log_to_console("Tab 5 (Health) rendering")
        render_health_tab()

    log_to_console("main() complete")


if __name__ == "__main__":
    main()
