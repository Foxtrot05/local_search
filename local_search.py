# local_search.py
import os
import requests
import trafilatura
import feedparser
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888/search")
OLLAMA_API = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
MAX_RESULTS = 3

# Derive Origin and Referer from SEARXNG_URL
searxng_parsed_url = urlparse(SEARXNG_URL)
SEARXNG_ORIGIN = f"{searxng_parsed_url.scheme}://{searxng_parsed_url.netloc}"

# Realistic browser-like headers
SEARCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": SEARXNG_ORIGIN,  # Critical for SearXNG, must match the base URL
    "Origin": SEARXNG_ORIGIN,
    "Connection": "keep-alive",
}

# === DATABASE ===
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def get_cached_content(url: str) -> str | None:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT content FROM web_cache WHERE url = %s", (url,))
            row = cur.fetchone()
            return row["content"] if row else None

def save_to_cache(url: str, content: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO web_cache (url, content)
                VALUES (%s, %s)
                ON CONFLICT (url) DO UPDATE SET content = EXCLUDED.content, fetched_at = NOW()
            """, (url, content))
            conn.commit()

# === WEB FETCHER ===
def fetch_clean_text(url: str, timeout: int = 10) -> str:
    try:
        headers = {"User-Agent": SEARCH_HEADERS["User-Agent"]}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        text = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
            output_format="txt"
        )
        return text or ""
    except Exception as e:
        print(f"[!] Failed to fetch {url}: {e}")
        return ""

# === LLM SUMMARIZER ===
def query_local_llm(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096
        }
    }
    try:
        resp = requests.post(OLLAMA_API, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"[!] LLM error: {e}")
        return "Error generating answer."
    
def parse_rss_results(rss_text: str) -> list[dict]:
    """Parse SearXNG RSS response into list of results."""
    try:
        feed = feedparser.parse(rss_text)
        results = []
        for entry in feed.entries:
            if entry.link:
                results.append({"title": entry.title, "url": entry.link, "content": entry.summary})
        return results
    except Exception as e: # feedparser is robust, but catch any unexpected errors
        print(f"[!] Feed parsing error: {e}")
        return []


# === MAIN SEARCH FUNCTION ===
def tavily_like_search(query: str) -> str:
    print(f"[+] Searching for: {query}")
    
    headers = SEARCH_HEADERS.copy()
    headers["Accept"] = "application/rss+xml, text/xml, */*"

    params = {
        "q": query,
        "format": "rss",        # ← Use RSS
        "language": "en",
        "pageno": 1,
    }

    try:
        resp = requests.get(SEARXNG_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        results = parse_rss_results(resp.text)
        
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (DNS failure, refused connection, etc)
        return f"[!] Search request failed: {e}"
    except Exception as e: # Catch other potential errors during the request
        return f"[!] Search failed: {e}"

    if not results:
        return "No search results found."

    top_results = results[:MAX_RESULTS]
    print(f"[+] Processing {len(top_results)} results...")

    contents = []
    for res in top_results:
        url = res.get("url", "")
        title = res.get("title", "No title")
        snippet = res.get("content", "")
        
        if not url or not urlparse(url).scheme in ("http", "https"):
            continue

        # Fetch full content
        content = get_cached_content(url)
        if not content:
            print(f"  → Fetching: {url}")
            content = fetch_clean_text(url)
            if content:
                save_to_cache(url, content)
            else:
                content = snippet or "No content available."

        contents.append(f"Title: {title}\nURL: {url}\nContent: {content[:2000]}")

    if not contents:
        return "No usable content retrieved."

    context = "\n\n---\n\n".join(contents)
    prompt = f"""Based on the following web search results, please answer the question.
Provide a concise answer (2-4 sentences) and cite the facts using the provided URLs.
If the information is not present in the results, state that you could not find a relevant answer.

Web Results:
{context}

---
Question: {query}

Answer:"""

    print("[+] Generating answer with LLM...")
    answer = query_local_llm(prompt)
    return answer

# === CLI TEST ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python local_search.py 'your question here'")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    result = tavily_like_search(question)
    print("\n" + "="*60)
    print(result)