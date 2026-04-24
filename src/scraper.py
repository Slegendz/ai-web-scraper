# import asyncio
# from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
# from urllib.parse import urljoin, urlparse


# async def crawl_site(start_url: str, max_pages: int = 5) -> list[dict]:
#     """BFS crawl starting from start_url, staying on the same domain."""
#     base_domain = urlparse(start_url).netloc
#     visited, queue, pages = set(), [start_url], []

#     config = CrawlerRunConfig(
#         word_count_threshold=10,
#         exclude_external_links=True,
#         remove_overlay_elements=True,
#     )

#     async with AsyncWebCrawler() as crawler:
#         while queue and len(visited) < max_pages:
#             url = queue.pop(0)
#             if url in visited:
#                 continue
#             visited.add(url)

#             try:
#                 result = await crawler.arun(url=url, config=config)
#             except Exception as e:
#                 print(f"[SKIP] {url} — {e}")
#                 continue

#             # Collect internal links for BFS
#             for link in result.links.get("internal", []):
#                 abs_url = urljoin(url, link.get("href", ""))
#                 if urlparse(abs_url).netloc == base_domain and abs_url not in visited:
#                     queue.append(abs_url)

#             print(result.markdown)
#             pages.append({
#                 "url": url,
#                 "markdown": result.markdown or ""
#             })
#             print(f"[OK] ({len(visited)}/{max_pages}) {url}")

#     return pages


import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from urllib.parse import urljoin, urlparse

from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter

url_filter = URLPatternFilter(patterns=["book", "book price"])

scorer = KeywordRelevanceScorer(
    keywords=["book", "book price"],
    weight=0.7
)

def get_config():
    """
    PruningContentFilter removes low-value blocks (navbars, ads, footers)
    fit_markdown is the clean LLM-ready output — much smaller than raw_markdown
    ignore_links removes [text](url) noise from markdown
    """

    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.0,          # 0.0–1.0: higher = more aggressive pruning
            threshold_type="fixed",
        ),
        options={"ignore_links": True}  
        # removes hyperlink clutter
    )

    return CrawlerRunConfig(
        # deep_crawl_strategy = BestFirstCrawlingStrategy(
        #     max_depth=5,
        #     filter_chain=FilterChain([url_filter]),
        #     include_external=False,
        #     url_scorer=scorer,
        #     max_pages=25,              # Maximum number of pages to crawl (optional)
        # ),
        # stream = True,

        # ── Content filtering ──────────────────────────────
        # word_count_threshold=150,          # skip tiny blocks like "Home | About"
        # excluded_tags=["nav", "footer", "header", "aside", "form", "noscript"],
        # exclude_external_links=True,
        # exclude_social_media_links=True,
        # remove_overlay_elements=True,     # removes cookie banners, modals

        # ── Markdown generation ────────────────────────────
        # markdown_generator=md_generator,  # uses PruningContentFilter

        # ── Performance ────────────────────────────────────
        cache_mode=CacheMode.ENABLED,     # cache pages, avoid re-fetching
        page_timeout=30000,               # 30s timeout per page
        verbose=False,
    )
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
        
async def crawl_site(start_url: str, max_pages: int = 5) -> list[dict]:
    base_domain = urlparse(start_url).netloc
    visited, queue, pages = set(), [start_url], []
    config = get_config()

    async with AsyncWebCrawler() as crawler:
        async for result in await crawler.arun(url=start_url, config = browser_cfg):
            if result.success:
                clean_text = result.markdown.fit_markdown or result.markdown.raw_markdown or ""
                
                print(f"[OK] {result.url} — {len(clean_text)} chars")
                print(clean_text)

                pages.append({
                    "url": result.url,
                    "markdown": clean_text
                })
            else:
                print(f"[ERROR] {result.url}: {result.error_message}")

            if len(pages) >= max_pages:
                break

    return pages



    #     while queue and len(visited) < max_pages:
    #         url = queue.pop(0)
    #         if url in visited:
    #             continue
    #         visited.add(url)

    #         try:
    #             result = await crawler.arun(url=url, config=config)
    #         except Exception as e:
    #             print(f"[SKIP] {url} — {e}")
    #             continue

    #         # if not result.success:
    #         #     print(f"[FAIL] {url} — {result.error_message}")
    #         #     continue
            
    #         # ✅ Use fit_markdown — pruned, clean, LLM-friendly
    #         clean_text = result.markdown.fit_markdown or result.markdown.raw_markdown or ""

    #         # Collect internal links for BFS
            # for link in result.links.get("internal", []):
            #     abs_url = urljoin(url, link.get("href", ""))
            #     if urlparse(abs_url).netloc == base_domain and abs_url not in visited:
            #         queue.append(abs_url)
            #         print(abs_url)

            # print(clean_text[:200])  # Print a snippet of the clean text
            # pages.append({"url": url, "markdown": clean_text})
            # print(f"[OK] ({len(visited)}/{max_pages}) {url} — {len(clean_text)} chars")

    # return pages

url="https://amazon.in"
pages = loop.run_until_complete(crawl_site(url, max_pages=50))