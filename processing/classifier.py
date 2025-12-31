"""
AI-powered post classification using Gemini Flash via OpenRouter.
Classifies posts to determine if they represent business opportunities.
"""
import json
import os
import sqlite3
import requests
from datetime import datetime


def get_db_path():
    """Get the database path based on environment."""
    if os.path.exists('/data'):
        return '/data/scraper.db'
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, 'data', 'scraper.db')


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def get_active_businesses():
    """Get all active businesses for the classification prompt."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, slug, domain, description
        FROM businesses
        WHERE is_active = 1
    ''')
    businesses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return businesses


def get_unanalyzed_posts(limit=10):
    """Get posts that haven't been analyzed yet."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.source, p.title, p.body, p.author, p.subreddit, p.url
        FROM posts p
        WHERE NOT EXISTS (
            SELECT 1 FROM analysis a WHERE a.post_id = p.id
        )
        ORDER BY p.scraped_at DESC
        LIMIT ?
    ''', (limit,))
    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts


def build_classification_prompt(post, businesses):
    """Build the classification prompt for a post."""
    # Build businesses list
    businesses_text = "\n".join([
        f"{i+1}. {b['name']} ({b['domain'] or 'no domain'}) - {b['description'] or 'No description'}"
        for i, b in enumerate(businesses)
    ])

    return f'''You are analyzing a social media post to determine if it's a business opportunity.

POST:
Source: {post['source']}
Subreddit/Community: {post.get('subreddit') or 'N/A'}
Title: {post.get('title') or 'N/A'}
Body: {post.get('body') or 'N/A'}
Author: {post.get('author') or 'N/A'}

BUSINESSES TO MATCH:
{businesses_text}

Return JSON only, no other text:
{{
  "relevant_to": ["business_slug"],
  "relevance_score": 1-10,
  "post_type": "pain_point|question|recommendation_request|competitor_complaint|other",
  "pain_score": 1-10,
  "urgency": "high|medium|low",
  "keywords_found": ["keyword1", "keyword2"],
  "competitor_mentioned": "competitor name or null",
  "suggested_response": "Helpful response suggestion or null",
  "reasoning": "Brief explanation"
}}

Be conservative with scores. Only 7+ if genuine business opportunity.'''


def classify_post(post, businesses, api_key):
    """
    Classify a single post using Gemini Flash.

    Returns:
        Dict with classification results or None if failed
    """
    prompt = build_classification_prompt(post, businesses)

    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://mikes-scraper.onrender.com',
                'X-Title': "Mike's Scraper"
            },
            json={
                'model': 'google/gemini-flash-1.5',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 1000
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"API error {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Parse JSON from response
        json_str = content
        if '```json' in content:
            json_str = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            json_str = content.split('```')[1].split('```')[0]

        return json.loads(json_str.strip())

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None
    except requests.Timeout:
        print("Request timed out")
        return None
    except Exception as e:
        print(f"Classification error: {e}")
        return None


def save_analysis(post_id, business_id, classification):
    """Save classification results to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO analysis (
            post_id, business_id, relevance_score, post_type, pain_score,
            urgency, keywords_matched, competitor_mentioned, suggested_response,
            status, analyzed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
    ''', (
        post_id,
        business_id,
        classification.get('relevance_score'),
        classification.get('post_type'),
        classification.get('pain_score'),
        classification.get('urgency'),
        json.dumps(classification.get('keywords_found', [])),
        classification.get('competitor_mentioned'),
        classification.get('suggested_response'),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def classify_posts(batch_size=10):
    """
    Main classification function.
    Processes unanalyzed posts in batches.

    Returns:
        Number of posts classified
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        return 0

    # Get active businesses
    businesses = get_active_businesses()
    if not businesses:
        print("No businesses configured, skipping classification")
        return 0

    # Create a slug->id mapping
    business_map = {b['slug']: b['id'] for b in businesses}

    # Get unanalyzed posts
    posts = get_unanalyzed_posts(batch_size)
    if not posts:
        print("No posts to classify")
        return 0

    print(f"Classifying {len(posts)} posts...")
    classified_count = 0

    for post in posts:
        print(f"  Classifying post {post['id']}: {(post.get('title') or '')[:50]}...")

        classification = classify_post(post, businesses, api_key)
        if not classification:
            print(f"    Failed to classify post {post['id']}")
            continue

        # Save analysis for each relevant business
        relevant_slugs = classification.get('relevant_to', [])
        if not relevant_slugs:
            # Still save with first business if no specific match
            business_id = businesses[0]['id']
            save_analysis(post['id'], business_id, classification)
        else:
            for slug in relevant_slugs:
                business_id = business_map.get(slug)
                if business_id:
                    save_analysis(post['id'], business_id, classification)

        classified_count += 1
        print(f"    Classified: relevance={classification.get('relevance_score')}, "
              f"type={classification.get('post_type')}, urgency={classification.get('urgency')}")

    return classified_count


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    count = classify_posts()
    print(f"Classification complete. Processed {count} posts.")
