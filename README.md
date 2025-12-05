Local AI Web Search – A Free, Self-Hosted Tavily Alternative
===========================================================

Overview
--------
This tool enables your AI applications to fetch, process, and summarize up-to-date information from the live web—without relying on paid APIs like Tavily. Built entirely with open-source software, it runs on your machine (or server) and respects your privacy.

How It Works
------------
1. 🔍 **Search**: Uses SearXNG (public instance or self-hosted) to find relevant URLs.
2. 🧹 **Clean**: Fetches each page and extracts human-readable text with `trafilatura`.
3. 💾 **Cache**: Stores results in a local PostgreSQL database to avoid re-fetching.
4. 🧠 **Answer**: Sends the cleaned content to a local LLM (via Ollama) to generate a concise, accurate response.

Requirements
------------
- Python 3.8+
- PostgreSQL database
- Ollama (https://ollama.com) with a local LLM installed (e.g., `phi3`, `mistral`, or `gemma:2b`)
- Internet connection (for web search)
- Optional: Self-hosted SearXNG for higher reliability (public instances may throttle requests)

Installation
------------
1. Install Ollama and pull a model:
   ollama pull phi3

2. Install Python dependencies:
   pip install -r requirements.txt

3. Set up configuration:
   Create a `.env` file in the project root (see Configuration below).

Usage
-----
Run from the command line:
   python local_search.py "What is the population of Japan in 2025?"

The script will:
- Search the web via SearXNG
- Extract and cache clean content
- Return an AI-generated answer using your local LLM

Configuration
-------------
Create a `.env` file in the same directory as `local_search.py` with the following variables:

   - SEARXNG_URL=http://localhost:8888/search
   - OLLAMA_MODEL=phi3
   - DB_HOST=localhost
   - DB_PORT=5432
   - DB_NAME=your_db_name
   - DB_USER=your_db_user
   - DB_PASSWORD=your_db_password

Ethical Use
-----------
- Please respect website terms of service and `robots.txt`.
- Add delays between requests (built-in).
- Use a descriptive User-Agent.
- Do not use for high-frequency scraping or commercial abuse.

License
-------
This project is open-source and free to use, modify, and distribute.  
Built with ❤️ using: SearXNG, trafilatura, Ollama, and PostgreSQL.

Note
----
Public SearXNG instances may be unreliable for automation. For production use, consider self-hosting SearXNG (see https://docs.searxng.org).
