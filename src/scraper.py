import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from urllib.parse import urljoin, urlparse


async def crawl_site(start_url: str, max_pages: int = 5) -> list[dict]:
    """BFS crawl starting from start_url, staying on the same domain."""
    base_domain = urlparse(start_url).netloc
    visited, queue, pages = set(), [start_url], []

    config = CrawlerRunConfig(
        word_count_threshold=10,
        exclude_external_links=True,
        remove_overlay_elements=True,
    )

    async with AsyncWebCrawler() as crawler:
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                result = await crawler.arun(url=url, config=config)
            except Exception as e:
                print(f"[SKIP] {url} — {e}")
                continue

            # Collect internal links for BFS
            for link in result.links.get("internal", []):
                abs_url = urljoin(url, link.get("href", ""))
                if urlparse(abs_url).netloc == base_domain and abs_url not in visited:
                    queue.append(abs_url)

            print(result.markdown)
            pages.append({
                "url": url,
                "markdown": result.markdown or ""
            })
            print(f"[OK] ({len(visited)}/{max_pages}) {url}")

    return pages