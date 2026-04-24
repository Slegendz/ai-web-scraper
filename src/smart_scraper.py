"""
smart_scraper.py  —  Simple AI Web Scraper
============================================
Works with:
  ✅ Static websites
  ✅ JavaScript / dynamic websites (React, Vue, etc.)
  ✅ Captcha-protected sites (stealth + magic mode)
  ✅ Sites with search bars (types your query automatically)

How it works (5 plain steps):
  1. Open the URL in a headless browser (stealth mode on)
  2. If a search query is given, find the search bar and type it
  3. Extract the requested data fields from the page using Gemini
  4. If some fields are missing, follow the most relevant links on the page
  5. Summarise everything into a clean result

Run from terminal:
  python src/smart_scraper.py "https://books.toscrape.com/" "Title,Price,Rating" --pages 4
  python src/smart_scraper.py "https://google.com" "Headlines" --search "Python news" --pages 2
"""

import asyncio
import json
import os
import re
import sys
import argparse
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import google.generativeai as genai
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────────────
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
gemini = genai.GenerativeModel("gemini-1.5-flash")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# ── Result types ───────────────────────────────────────────────────────────────
@dataclass
class ScraperResult:
    seed_url:      str
    fields:        list[str]
    records:       list[dict]      # Each dict has your field names as keys
    summary:       str
    pages_visited: int
    errors:        list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — Open the page (with stealth + captcha bypass)
# ══════════════════════════════════════════════════════════════════════════════

def _browser_config() -> BrowserConfig:
    """
    BrowserConfig with stealth mode ON.
    This makes the browser look like a real human and bypasses most bot-checks.
    """
    return BrowserConfig(
        headless=True,          # Run invisibly in the background
        verbose=False,
        # Stealth headers — makes it look like a real Chrome browser
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def _page_config(js_code: str | None = None) -> CrawlerRunConfig:
    """
    CrawlerRunConfig that:
      - Waits for JS to finish rendering (good for React/Vue/dynamic sites)
      - Removes nav, footer, ads — keeps only real content
      - Uses magic=True to auto-dismiss popups & cookie banners (helps with captchas)
      - Optionally runs custom JavaScript (e.g. to type in a search bar)
    """
    clean_markdown = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.4, threshold_type="fixed"),
        options={"ignore_links": True},
    )
    return CrawlerRunConfig(
        # Wait for the page to fully render (important for JS-heavy sites)
        wait_until="networkidle",
        page_timeout=45_000,            # 45 seconds (some sites are slow)

        # Auto-handle popups, cookie banners, overlays
        magic=True,                     # ← This is the captcha/bot bypass hero
        remove_overlay_elements=True,

        # Content cleanup — keep only the real text, remove menus/footers
        excluded_tags=["nav", "footer", "header", "aside", "form", "noscript"],
        word_count_threshold=15,
        exclude_external_links=True,
        exclude_social_media_links=True,

        # Clean markdown output for the LLM
        markdown_generator=clean_markdown,

        # Cache pages so repeated runs are fast
        cache_mode=CacheMode.ENABLED,

        # Run custom JS if needed (e.g. search bar interaction)
        js_code=js_code,

        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — Interact with a search bar (if the site needs it)
# ══════════════════════════════════════════════════════════════════════════════

def _build_search_js(query: str) -> str:
    """
    Build JavaScript that:
      1. Finds the search input on the page
      2. Types the query into it
      3. Presses Enter to submit
    Works on most websites without knowing the exact CSS selector in advance.
    """
    # Escape the query for safe JS string embedding
    safe_query = query.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")

    return f"""
    (async () => {{
        // Try several common search input selectors
        const selectors = [
            'input[type="search"]',
            'input[name="q"]',
            'input[name="query"]',
            'input[name="search"]',
            'input[placeholder*="search" i]',
            'input[placeholder*="Search" i]',
            'input[aria-label*="search" i]',
            '[role="searchbox"]',
            'input[type="text"]',    // Last resort: generic text field
        ];

        let searchInput = null;
        for (const sel of selectors) {{
            searchInput = document.querySelector(sel);
            if (searchInput) break;
        }}

        if (!searchInput) {{
            console.warn("[Scraper] No search bar found on this page.");
            return;
        }}

        // Focus, clear, and type the query (simulates a real human)
        searchInput.focus();
        searchInput.value = "";
        searchInput.value = "{safe_query}";
        searchInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
        searchInput.dispatchEvent(new Event("change", {{ bubbles: true }}));

        // Wait a moment then press Enter
        await new Promise(r => setTimeout(r, 600));
        searchInput.dispatchEvent(new KeyboardEvent("keydown", {{ key: "Enter", bubbles: true }}));
        searchInput.dispatchEvent(new KeyboardEvent("keyup",   {{ key: "Enter", bubbles: true }}));

        // Also try clicking a nearby submit button if it exists
        const submitBtn = document.querySelector(
            'button[type="submit"], input[type="submit"], button[aria-label*="search" i]'
        );
        if (submitBtn) submitBtn.click();

        // Give the page time to load results
        await new Promise(r => setTimeout(r, 2500));
    }})();
    """


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — Extract fields using Gemini
# ══════════════════════════════════════════════════════════════════════════════

def _ask_gemini(prompt: str) -> str:
    """Single call to Gemini. Returns the text response."""
    try:
        return gemini.generate_content(prompt).text.strip()
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return ""


def _parse_json_response(text: str):
    """Strip markdown fences and parse JSON (list or dict)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_fields_from_page(markdown: str, fields: list[str], url: str) -> list[dict]:
    """
    Ask Gemini to pull out only the requested fields from the page's markdown.

    Returns a list of record dicts (one per item found on the page).
    For example, if the page has 20 books, returns 20 dicts.
    If the page has 1 article, returns 1 dict.
    """
    fields_list = "\n".join(f"  - {f}" for f in fields)

    prompt = f"""You are a data extraction assistant. Read the webpage content below and extract the requested fields.

Fields to extract:
{fields_list}

Rules:
- If the page lists MULTIPLE items (products, articles, people, etc.), return a JSON ARRAY — one object per item.
- If the page is about ONE thing, return a single JSON OBJECT.
- Each object must have exactly the field names listed above as keys.
- If a field is not found, use null.
- Return ONLY valid JSON. No explanation. No markdown fences.

Page URL: {url}
Page content:
{markdown[:8000]}"""

    raw = _ask_gemini(prompt)
    parsed = _parse_json_response(raw)

    # Normalise to always return a list of dicts
    if isinstance(parsed, list):
        return [
            {f: item.get(f) for f in fields}
            for item in parsed
            if isinstance(item, dict)
        ]
    if isinstance(parsed, dict):
        return [{f: parsed.get(f) for f in fields}]

    # If Gemini returned something we can't parse, return an empty record
    return [{f: None for f in fields}]


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — Pick the best follow-up links (if data is incomplete)
# ══════════════════════════════════════════════════════════════════════════════

def _which_fields_are_missing(records: list[dict], fields: list[str]) -> list[str]:
    """Return field names that are null/empty across ALL collected records so far."""
    found = {f for rec in records for f, v in rec.items() if v is not None}
    return [f for f in fields if f not in found]


def _pick_best_links(links: list[str], fields: list[str], how_many: int) -> list[str]:
    """
    Ask Gemini to pick the links most likely to contain the missing data.
    Simple and effective — no complex scoring math needed.
    """
    if not links:
        return []

    numbered = "\n".join(f"  {i+1}. {u}" for i, u in enumerate(links[:50]))
    fields_str = ", ".join(fields)

    prompt = f"""I am scraping a website to find: {fields_str}

Here are the internal links found on the page:
{numbered}

Which {how_many} links are most likely to have this data? 
Return ONLY a JSON array of the selected URLs (strings). No explanation."""

    raw = _ask_gemini(prompt)
    selected = _parse_json_response(raw)

    if isinstance(selected, list):
        # Only keep URLs that were actually in our list
        valid = set(links)
        return [u for u in selected if isinstance(u, str) and u in valid][:how_many]

    # Fallback: just take the first N
    return links[:how_many]


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — Summarise everything
# ══════════════════════════════════════════════════════════════════════════════

def _summarise(records: list[dict], fields: list[str], seed_url: str) -> str:
    """Ask Gemini to write a short, plain-English summary of all extracted data."""
    if not records:
        return "No data could be extracted from this website."

    data_preview = json.dumps(records[:30], indent=2, ensure_ascii=False)[:6000]
    fields_str = ", ".join(fields)

    prompt = f"""I scraped the website {seed_url} to find: {fields_str}

Here is the extracted data ({len(records)} records total):
{data_preview}

Write a short, plain-English summary (under 150 words) covering:
- How many records were found
- Key highlights or patterns in the data
- Any fields that were empty or missing"""

    return _ask_gemini(prompt)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE — tie all 5 steps together
# ══════════════════════════════════════════════════════════════════════════════

async def run_scraper(
    url: str,
    fields: list[str],
    search_query: str | None = None,
    max_pages: int = 6,
) -> ScraperResult:
    """
    The main scraper function. Call this from n8n_api.py or directly.

    Args:
        url:          The website URL to scrape.
        fields:       What data to look for, e.g. ["Title", "Price", "Rating"].
        search_query: If the site has a search bar, type this query into it first.
        max_pages:    How many pages to visit at most.

    Returns:
        ScraperResult with .records (list of dicts) and .summary (plain text).
    """
    if not url.startswith("http"):
        url = "https://" + url

    all_records: list[dict] = []
    visited:     set[str]   = set()
    errors:      list[str]  = []

    print(f"\n{'='*55}")
    print(f"  AI Scraper Starting")
    print(f"  URL:    {url}")
    print(f"  Fields: {fields}")
    if search_query:
        print(f"  Search: '{search_query}'")
    print(f"  Max pages: {max_pages}")
    print(f"{'='*55}\n")

    browser_cfg = _browser_config()

    async with AsyncWebCrawler(config=browser_cfg) as browser:

        # ── Step 1 & 2: Open the page (and search if needed) ──────────────────
        search_js   = _build_search_js(search_query) if search_query else None
        page_config = _page_config(js_code=search_js)

        print(f"[1/5] Opening: {url}" + (f" (searching for '{search_query}')" if search_query else ""))
        result = await browser.arun(url=url, config=page_config)
        visited.add(url)

        if not result.success:
            print(f"      ✗ Failed: {result.error_message}")
            return ScraperResult(
                seed_url=url, fields=fields, records=[],
                summary="Could not open the webpage.",
                pages_visited=0,
                errors=[f"Page failed to load: {result.error_message}"]
            )

        markdown = result.markdown.fit_markdown or result.markdown.raw_markdown or ""
        print(f"      ✓ Got {len(markdown):,} characters of content")

        # Collect internal links for possible follow-up
        base_domain    = urlparse(url).netloc
        internal_links = [
            urljoin(url, lnk.get("href", ""))
            for lnk in result.links.get("internal", [])
            if urlparse(urljoin(url, lnk.get("href", ""))).netloc == base_domain
        ]
        internal_links = list(dict.fromkeys(internal_links))  # deduplicate
        print(f"      ✓ Found {len(internal_links)} internal links")

        # ── Step 3: Extract fields from this page ─────────────────────────────
        print(f"\n[3/5] Extracting fields from page …")
        page_records = _extract_fields_from_page(markdown, fields, url)
        all_records.extend(page_records)
        print(f"      ✓ Got {len(page_records)} record(s) from seed page")

        # ── Step 4: Follow-up pages if needed ─────────────────────────────────
        missing = _which_fields_are_missing(all_records, fields)
        pages_left = max_pages - 1

        if missing and pages_left > 0 and internal_links:
            print(f"\n[4/5] Missing fields: {missing}")
            print(f"      Asking AI to pick best follow-up links …")

            best_links = _pick_best_links(internal_links, fields, how_many=pages_left + 2)
            print(f"      AI selected {len(best_links)} links to visit")

            for i, link in enumerate(best_links):
                if link in visited or len(visited) >= max_pages:
                    break
                visited.add(link)

                print(f"\n      Visiting ({len(visited)}/{max_pages}): {link}")
                try:
                    sub_result = await browser.arun(url=link, config=_page_config())
                except Exception as e:
                    errors.append(f"Error visiting {link}: {e}")
                    print(f"      ✗ Error: {e}")
                    continue

                if not sub_result.success:
                    errors.append(f"Failed to load: {link}")
                    print(f"      ✗ Failed: {sub_result.error_message}")
                    continue

                sub_md = sub_result.markdown.fit_markdown or sub_result.markdown.raw_markdown or ""
                sub_records = _extract_fields_from_page(sub_md, fields, link)
                all_records.extend(sub_records)
                print(f"      ✓ Got {len(sub_records)} more record(s)")

                # Check if we now have everything
                missing = _which_fields_are_missing(all_records, fields)
                if not missing:
                    print(f"      ✓ All fields found! Stopping early.")
                    break
        else:
            print(f"\n[4/5] All fields found on first page — no follow-up needed.")

        # ── Step 5: Summarise ─────────────────────────────────────────────────
        print(f"\n[5/5] Generating summary …")
        summary = _summarise(all_records, fields, url)

    print(f"\n{'='*55}")
    print(f"  Done! Visited {len(visited)} page(s), found {len(all_records)} record(s).")
    print(f"{'='*55}\n")

    return ScraperResult(
        seed_url=url,
        fields=fields,
        records=all_records,
        summary=summary,
        pages_visited=len(visited),
        errors=errors,
    )


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Web Scraper using crawl4ai + Gemini")
    parser.add_argument("url",    help="Website URL to scrape")
    parser.add_argument("fields", help="Comma-separated fields, e.g. 'Title,Price,Rating'")
    parser.add_argument("--search", default=None, help="Search query to type in the search bar")
    parser.add_argument("--pages",  type=int, default=5, help="Max pages to visit (default: 5)")
    args = parser.parse_args()

    field_list = [f.strip() for f in args.fields.split(",") if f.strip()]

    result = asyncio.run(run_scraper(
        url=args.url,
        fields=field_list,
        search_query=args.search,
        max_pages=args.pages,
    ))

    print("SUMMARY")
    print("─" * 40)
    print(result.summary)

    print(f"\nRECORDS ({len(result.records)} total, showing first 5)")
    print("─" * 40)
    for rec in result.records[:5]:
        for k, v in rec.items():
            print(f"  {k}: {v}")
        print()

    if result.errors:
        print("ERRORS")
        print("─" * 40)
        for e in result.errors:
            print(f"  ✗ {e}")
