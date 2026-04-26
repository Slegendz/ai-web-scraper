from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from urllib.parse import urljoin, urlparse, unquote
from src.utils import extract_link_text
from config import SKIP_EXT

def parse_links(html_links: list, base_url: str) -> list:
    base_domain = urlparse(base_url).netloc
    links = []

    for link in html_links:
        href = link.get("href", "")
        abs_url = urljoin(base_url, href)

        if not abs_url.startswith("http"):
            continue
        if urlparse(abs_url).netloc != base_domain:
            continue
        if any(p in abs_url.lower() for p in SKIP_EXT):
            continue

        text = extract_link_text(link, abs_url)
        if text:
            links.append({"text": text, "url": unquote(abs_url)})
    return links


# Crawl4Ai scraper
async def crawl(url: str) -> dict:
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=60000,
        delay_before_return_html=3.0,
        remove_overlay_elements=True,
        excluded_tags=["footer", "header", "aside", "noscript"],
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.3),
            options={"ignore_links": False},
        ),
        magic=True,
        simulate_user=True,
        override_navigator=True,
        verbose=False,
    )

    browser = BrowserConfig(
        headless=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    )

    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=url, config=config)
        
        if not result.success:
            return {
                "url": url,
                "content": "",
                "links": [],
                "error": result.error_message,
            }

        content = ""
        if result.markdown:
            content = result.markdown.fit_markdown or result.markdown.raw_markdown or ""

        links = parse_links(result.links.get("internal", []), url)
        return {"url": url, "content": content, "links": links, "error": None}
