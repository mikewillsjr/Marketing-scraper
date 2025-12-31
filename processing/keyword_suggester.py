"""
AI-powered keyword suggestion using 4 models via OpenRouter.
Queries GPT-4o, Claude Opus 4.5, DeepSeek, and Gemini 2.5 in parallel.
"""
import asyncio
import json
import os
import aiohttp
from typing import Optional


# Model configuration with display names and colors
MODELS = {
    'openai/gpt-5.2': {
        'name': 'gpt-5.2',
        'display': 'GPT-5.2',
        'color': 'blue'
    },
    'anthropic/claude-opus-4.5': {
        'name': 'claude-opus-4.5',
        'display': 'Claude Opus 4.5',
        'color': 'orange'
    },
    'google/gemini-3-pro-preview': {
        'name': 'gemini-3-pro',
        'display': 'Gemini 3 Pro',
        'color': 'red'
    }
}


def build_prompt(name: str, domain: str, description: str, spec_text: str) -> str:
    """Build the keyword suggestion prompt."""
    return f'''You are helping set up social media monitoring for a business. Based on the business information below, suggest keywords and phrases to monitor on social media (Reddit, Twitter, TikTok, Instagram, Hacker News).

BUSINESS NAME: {name}
DOMAIN: {domain if domain else "Not provided"}

DESCRIPTION:
{description if description else "Not provided"}

ADDITIONAL DOCUMENTS/CONTEXT:
{spec_text if spec_text else "Not provided"}

Generate keywords in these categories:
1. "direct" - Direct product/service terms (what the business offers)
2. "pain_point" - Problem phrases (what pain points customers have that this solves)
3. "question" - Question phrases (how people ask for help with this)
4. "competitor" - Competitor names (known alternatives in this space)
5. "industry" - Industry terms (general category terms)

Return JSON only, no other text:
{{
  "keywords": [
    {{"keyword": "example phrase", "category": "direct"}},
    {{"keyword": "another phrase", "category": "pain_point"}},
    ...
  ]
}}

Generate 20-40 keywords. Focus on phrases people actually type when looking for help, not marketing speak. Include common misspellings if relevant. Be thorough.'''


async def query_model(session: aiohttp.ClientSession, model_id: str, prompt: str, api_key: str) -> dict:
    """
    Query a single model via OpenRouter.

    Returns:
        Dict with 'model', 'keywords' (list), and 'error' (if any)
    """
    model_info = MODELS[model_id]
    result = {
        'model': model_info['name'],
        'display': model_info['display'],
        'color': model_info['color'],
        'keywords': [],
        'error': None
    }

    try:
        async with session.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://mikes-scraper.onrender.com',
                'X-Title': "Mike's Scraper"
            },
            json={
                'model': model_id,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 4000
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                result['error'] = f"API error {response.status}: {error_text[:200]}"
                return result

            data = await response.json()

            # Extract content from response
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

            # Parse JSON from response (handle markdown code blocks)
            json_str = content
            if '```json' in content:
                json_str = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                json_str = content.split('```')[1].split('```')[0]

            parsed = json.loads(json_str.strip())
            result['keywords'] = parsed.get('keywords', [])

    except json.JSONDecodeError as e:
        result['error'] = f"JSON parse error: {str(e)[:100]}"
    except asyncio.TimeoutError:
        result['error'] = "Request timed out"
    except Exception as e:
        result['error'] = f"Error: {str(e)[:100]}"

    return result


async def suggest_keywords(name: str, domain: str, description: str, spec_text: str) -> list:
    """
    Query all 4 models in parallel for keyword suggestions.

    Args:
        name: Business name
        domain: Business domain (optional)
        description: Business description (optional)
        spec_text: Additional context/documents (optional)

    Returns:
        List of dicts with:
        {
            "keyword": "the keyword",
            "category": "direct|pain_point|question|competitor|industry",
            "models": ["gpt-4o", "claude-opus-4.5", ...],
            "model_count": 3
        }
    """
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")

    prompt = build_prompt(name, domain, description, spec_text)

    # Query all models in parallel
    async with aiohttp.ClientSession() as session:
        tasks = [
            query_model(session, model_id, prompt, api_key)
            for model_id in MODELS.keys()
        ]
        results = await asyncio.gather(*tasks)

    # Combine and deduplicate keywords
    keyword_map = {}  # keyword -> {category, models: set}

    for result in results:
        if result['error']:
            print(f"Warning: {result['display']} failed: {result['error']}")
            continue

        model_name = result['model']
        for kw in result['keywords']:
            keyword = kw.get('keyword', '').strip()
            category = kw.get('category', 'direct')

            if not keyword:
                continue

            if keyword not in keyword_map:
                keyword_map[keyword] = {
                    'keyword': keyword,
                    'category': category,
                    'models': set()
                }
            keyword_map[keyword]['models'].add(model_name)

    # Convert to list format
    combined = []
    for kw_data in keyword_map.values():
        combined.append({
            'keyword': kw_data['keyword'],
            'category': kw_data['category'],
            'models': sorted(list(kw_data['models'])),
            'model_count': len(kw_data['models'])
        })

    # Sort by model_count (most agreement first), then alphabetically
    combined.sort(key=lambda x: (-x['model_count'], x['keyword'].lower()))

    return combined


def suggest_keywords_sync(name: str, domain: str, description: str, spec_text: str) -> list:
    """
    Synchronous wrapper for suggest_keywords.
    Use this when calling from non-async code (like Streamlit).
    """
    return asyncio.run(suggest_keywords(name, domain, description, spec_text))


# Model color mapping for UI
MODEL_COLORS = {
    'gpt-5.2': '#3B82F6',        # blue
    'claude-opus-4.5': '#F97316', # orange
    'gemini-3-pro': '#EF4444'     # red
}

MODEL_EMOJIS = {
    'gpt-5.2': '🔵',
    'claude-opus-4.5': '🟠',
    'gemini-3-pro': '🔴'
}
