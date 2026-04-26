import asyncio
from datetime import datetime
from src.crawler import crawl
from src.extractor import extract_homepage_data, pick_best_links, validate_page
from src.validator import check_homepage_sufficient

# Scraping Steps
async def scrape(url: str, fields: list) -> dict:
    timestamp = datetime.now().isoformat()
    print(f"Scraping: {url} | Fields: {fields}")

    # Crawl homepage
    page = await crawl(url)
    if not page["content"]:
        return {
            "success": False,
            "error": page.get("error", "Empty content"),
            "timestamp": timestamp,
        }
    print(f"Crawled — {len(page['content'])} chars, {len(page['links'])} links")

    # Extracting Homepage content
    extracted = extract_homepage_data(page["content"], fields)
    print(f"Extracted {len(extracted)} items")

    # Checking if content is enough
    sufficiency = check_homepage_sufficient(extracted, fields)
    print(f"Homepage sufficient: {sufficiency.get('homepage_sufficient')}")

    if sufficiency.get("homepage_sufficient"):
        return {
            "success": True,
            "data": extracted,
            "count": len(extracted),
            "source": "homepage",
            "reasoning": sufficiency.get("reasoning"),
            "timestamp": timestamp,
        }

    # Step 3 — Pick best links
    print("Going deeper into links...")
    best_links = pick_best_links(page["links"], fields)
    print(f"Best links: {best_links}")

    if not best_links:
        return {
            "success": False,
            "data": extracted,
            "source": "homepage_partial",
            "timestamp": timestamp,
        }

    # Step 4 — Loop through links
    collected = []
    for link_url in best_links:
        print(f"Scraping link: {link_url}")
        await asyncio.sleep(2)

        link_page = await crawl(link_url)
        if not link_page["content"]:
            continue

        validation = validate_page(link_page["content"], link_url, fields)
        if validation.get("is_sufficient") and validation.get("extracted_data"):
            data = validation["extracted_data"]
            collected.extend(data if isinstance(data, list) else [data])
            print(f"{len(data) if isinstance(data, list) else 1} items")

    if not collected:
        return {
            "success": False,
            "data": extracted,
            "source": "none",
            "timestamp": timestamp,
        }

    return {
        "success": True,
        "data": collected,
        "count": len(collected),
        "source": "deep_crawl",
        "timestamp": timestamp,
    }
