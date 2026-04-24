"""
scraper3.py  —  Amazon.in Scraper (Anti-Detection + Focused Parsing)
======================================================================
Scrapes Amazon.in search results without getting blocked.

Key techniques used:
  ✅ Non-headless browser (headless=False) — Amazon detects headless easily
  ✅ Stealth mode + random user agent — bypasses fingerprinting
  ✅ Human-like delays — mimics real user behaviour
  ✅ css_selector — parses ONLY product cards, ignores everything else
  ✅ Gemini structured extraction — pulls clean fields from the markdown
  ✅ CacheMode.BYPASS — always fetches fresh results

Run:
    python src/scraper3.py
    python src/scraper3.py "wireless headphones" 2

Output:
    Prints a JSON list of products to the console.
    Saves results to  amazon_results.json  in the project root.
"""

import asyncio
import json
import os
import re
import sys
import time
import random
from dataclasses import dataclass

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


# ── Output model ───────────────────────────────────────────────────────────────
@dataclass
class Product:
    name:         str
    price:        str | None
    rating:       str | None
    review_count: str | None
    availability: str | None
    url:          str | None


# ══════════════════════════════════════════════════════════════════════════════
#  1. BROWSER CONFIG  —  the anti-detection setup
#     headless=False  is intentional: Amazon aggressively blocks headless
#     Chrome. This makes the browser look exactly like a real desktop session.
# ══════════════════════════════════════════════════════════════════════════════

def amazon_browser() -> BrowserConfig:
    return BrowserConfig(
        browser_type="chromium",

        # ── MOST IMPORTANT: headless=False ────────────────────────────────
        # Amazon's bot detection (Perimeter X / DataDome) checks for
        # dozens of browser signals. A visible window passes nearly all of them.
        headless=False,

        # Stealth mode patches common automation fingerprints
        # (navigator.webdriver, chrome runtime, plugins list, etc.)
        enable_stealth=True,

        # Rotate user-agent automatically so each session looks different
        user_agent_mode="random",

        # Extra headers that real Chrome sends — absence of these is a bot signal
        headers={
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "DNT":             "1",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  2. PAGE CONFIG  —  focused parsing (only product cards)
#     We use css_selector to tell crawl4ai to look ONLY at the product grid.
#     This keeps the markdown tiny and LLM-friendly, and avoids nav/ads noise.
# ══════════════════════════════════════════════════════════════════════════════

def amazon_page_config(wait_for_selector: str | None = None) -> CrawlerRunConfig:
    """
    Args:
        wait_for_selector: Optional CSS selector to wait for before parsing.
                           Use this after a search to wait for results to appear.
    """
    # Only keep the text content — strip links/images from markdown
    # (we don't need them; Gemini works better on clean text)
    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.3, threshold_type="fixed"),
        options={
            "ignore_links":  True,
            "ignore_images": True,
        },
    )

    # ── Amazon product card selectors (both old and new Amazon layouts) ──
    # Priority: new layout first, old layout as fallback
    PRODUCT_GRID = (
        "[data-component-type='s-search-result'], "  # main search result card
        ".s-result-list .s-result-item, "            # list layout
        "#search .s-main-slot"                        # entire results slot fallback
    )

    return CrawlerRunConfig(
        # ── Only parse the product area — ignore nav, header, ads, footer ──
        css_selector=PRODUCT_GRID,

        # ── Wait for JS-rendered results ─────────────────────────────────
        wait_until="networkidle",
        page_timeout=45_000,

        # Human-like delay BEFORE reading the page (2–4 seconds random)
        delay_before_scraping=random.uniform(2.0, 4.0),

        # Optionally wait for a specific element after search
        wait_for=f"css={wait_for_selector}" if wait_for_selector else None,

        # ── Bot-bypass helpers ────────────────────────────────────────────
        magic=True,                     # auto-dismiss popups, cookie banners
        remove_overlay_elements=True,   # removes overlay divs that block content

        # Always fetch fresh — never serve cached Amazon pages
        cache_mode=CacheMode.BYPASS,

        # ── Markdown generation ───────────────────────────────────────────
        markdown_generator=md_gen,

        # No minimum word count — product cards can be short
        word_count_threshold=5,

        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  3. SEARCH JAVASCRIPT  —  types the query and submits
#     We inject JS directly into the page so crawl4ai controls the browser
#     like a human would (instead of constructing a search URL manually).
# ══════════════════════════════════════════════════════════════════════════════

def search_js(query: str) -> str:
    """JavaScript that types the search query and presses Enter."""
    safe_q = query.replace("'", "\\'").replace('"', '\\"')
    return f"""
    (async () => {{
        // Amazon's search box selector
        const box = document.querySelector(
            '#twotabsearchtextbox, input[name="field-keywords"], input[type="search"]'
        );
        if (!box) {{ console.warn('Search box not found'); return; }}

        // Clear, then type the query (simulates real typing)
        box.focus();
        box.value = '';
        box.value = '{safe_q}';
        box.dispatchEvent(new Event('input',  {{ bubbles: true }}));
        box.dispatchEvent(new Event('change', {{ bubbles: true }}));

        // Small pause then submit
        await new Promise(r => setTimeout(r, 800));

        const btn = document.querySelector('#nav-search-submit-button, [type="submit"]');
        if (btn) btn.click();
        else box.form?.submit();

        // Wait for results to start loading
        await new Promise(r => setTimeout(r, 2500));
    }})();
    """


# ══════════════════════════════════════════════════════════════════════════════
#  4. GEMINI EXTRACTION  —  parse only what we need
#     Gemini reads the clean markdown and returns structured JSON.
#     We keep the prompt very specific so it doesn't hallucinate.
# ══════════════════════════════════════════════════════════════════════════════

def extract_products_with_gemini(markdown: str, query: str) -> list[dict]:
    """
    Ask Gemini to extract product data from the Amazon search result markdown.
    Returns a list of product dicts.
    """
    prompt = f"""You are an Amazon data parser. Read the product listing below and extract products.

For each product return a JSON object with these exact keys:
  - name          : full product name (string)
  - price         : price in ₹ (string, e.g. "₹12,499") — null if not shown
  - rating        : star rating (string, e.g. "4.2 out of 5") — null if not shown
  - review_count  : number of ratings (string, e.g. "1,234 ratings") — null if not shown
  - availability  : stock status if visible (string) — null if not shown

Return a JSON ARRAY of these objects.
Rules:
- Include only real products (skip ads, banners, sponsored noise)
- If a field is genuinely missing, use null — do NOT guess
- Return ONLY valid JSON, no explanation, no markdown fences

Search query: "{query}"
Amazon search result content:
{markdown[:10000]}"""

    try:
        raw = gemini.generate_content(prompt).text.strip()
        # Strip markdown fences if Gemini adds them
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "results" in parsed:
            return parsed["results"]
        return []
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  5. MAIN FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_amazon(
    query:      str,
    max_pages:  int = 1,
    output_file: str = "amazon_results.json",
) -> list[dict]:
    """
    Scrape Amazon.in search results for the given query.

    Args:
        query:       What to search for, e.g. "wireless headphones under 2000"
        max_pages:   How many result pages to scrape (default: 1)
        output_file: Where to save the JSON output

    Returns:
        List of product dicts with name, price, rating, review_count, availability.
    """
    print(f"\n{'='*55}")
    print(f"  Amazon.in Scraper")
    print(f"  Query:     {query}")
    print(f"  Max pages: {max_pages}")
    print(f"{'='*55}\n")

    all_products: list[dict] = []
    browser_cfg = amazon_browser()

    async with AsyncWebCrawler(config=browser_cfg) as browser:

        for page_num in range(1, max_pages + 1):

            # ── Build the URL ──────────────────────────────────────────────
            if page_num == 1:
                # For page 1: open amazon.in and use the search bar
                # (more human-like than constructing a search URL directly)
                target_url = "https://www.amazon.in"
                js = search_js(query)
                wait_for = "data-component-type"   # wait for results to appear
            else:
                # For pages 2+: construct the paginated search URL directly
                encoded_q = query.replace(" ", "+")
                target_url = f"https://www.amazon.in/s?k={encoded_q}&page={page_num}"
                js = None
                wait_for = None

            print(f"[Page {page_num}/{max_pages}] Opening: {target_url}")

            # Add a random pause between pages to look human
            if page_num > 1:
                pause = random.uniform(3.0, 6.0)
                print(f"  Waiting {pause:.1f}s before next page …")
                await asyncio.sleep(pause)

            # ── Crawl the page ─────────────────────────────────────────────
            config = amazon_page_config(wait_for_selector=wait_for)
            if js:
                config.js_code = js

            result = await browser.arun(url=target_url, config=config)

            if not result.success:
                print(f"  ✗ Page {page_num} failed: {result.error_message}")
                continue

            # ── Get the clean markdown ─────────────────────────────────────
            markdown = result.markdown.fit_markdown or result.markdown.raw_markdown or ""
            print(f"  ✓ Got {len(markdown):,} characters of content")

            if len(markdown) < 200:
                print(f"  ⚠️  Very little content — Amazon may have blocked this request.")
                print(f"     Try again in a few minutes, or check if CAPTCHA appeared.")
                break

            # ── Extract products with Gemini ───────────────────────────────
            print(f"  Extracting products with Gemini …")
            products = extract_products_with_gemini(markdown, query)
            print(f"  ✓ Extracted {len(products)} product(s) from page {page_num}")

            all_products.extend(products)

    # ── Save results ───────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  Done! Total products found: {len(all_products)}")

    if all_products:
        out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_file)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=2, ensure_ascii=False)
        print(f"  Saved to: {out_path}")

    print(f"{'='*55}\n")
    return all_products


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Default search — override with command line args:
    #   python src/scraper3.py "gaming mouse under 1500" 2
    query     = sys.argv[1] if len(sys.argv) > 1 else "wireless earbuds under 2000"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    products = asyncio.run(scrape_amazon(query, max_pages))

    print(f"\n  Results ({len(products)} products):")
    print("─" * 55)
    for i, p in enumerate(products, 1):
        print(f"\n  {i}. {p.get('name', 'N/A')[:80]}")
        print(f"     Price:   {p.get('price',        'N/A')}")
        print(f"     Rating:  {p.get('rating',       'N/A')}")
        print(f"     Reviews: {p.get('review_count', 'N/A')}")
