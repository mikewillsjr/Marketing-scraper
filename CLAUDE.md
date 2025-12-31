# CLAUDE.md

## About the Human

Mike is not a developer but follows directions extremely well. He needs:
- Exact file paths and locations
- Explicit instructions on what goes where
- No assumptions about technical knowledge
- Clear "do this, then this" steps

## Communication Style

- Be direct and concise
- Use tables and lists for clarity
- Don't explain the "why" unless asked
- When something breaks, give the exact fix - not options to consider
- Never say "you could do X or Y" - just tell him what to do

## Project Context

This is Mike's private market intelligence tool called "Mike's Scraper". It monitors social media for business opportunities across multiple businesses he owns/operates.

Key facts:
- Hosted on Render (web service + cron jobs)
- SQLite database stored at /data/scraper.db (Render) or ./data/scraper.db (local)
- Uses OpenRouter for all AI (keyword suggestions + post classification)
- Streamlit dashboard is the main interface
- No alerts for now - just dashboard

## Technical Preferences

- Keep it simple - no over-engineering
- Graceful failures everywhere - one broken scraper should never crash the app
- All scrapers exit with code 0 even on failure
- Database path auto-detects: /data if exists, else ./data
- Environment variables for secrets only (OPENROUTER_API_KEY)

## When Things Break

1. Give the exact error message
2. Give the exact file and line if possible
3. Give the exact fix to copy/paste
4. Tell him exactly where to paste it

Do not:
- Offer multiple solutions
- Explain the underlying concepts
- Suggest "debugging steps"

## File Creation

When creating or editing files:
- Always show the complete file content
- Always confirm the file path
- Never show partial snippets and say "add this somewhere"
- If editing an existing file, show the full updated file or exact line numbers

## Testing

After building something:
- Give him the exact command to test it
- Tell him what success looks like
- Tell him what failure looks like and what to do

## Questions

Don't ask clarifying questions unless absolutely necessary. Make reasonable decisions based on context. Mike will tell you if something isn't right.
