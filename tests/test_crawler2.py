import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

async def main():
    # 1. Define what "Relevant" means for your project
    user_target_fields = ["revenue", "net income", "key products", "annual report"]
    
    # 2. Use a Scorer to prioritize the links
    # This gives higher 'points' to URLs containing your target fields
    scorer = KeywordRelevanceScorer(
        keywords=user_target_fields,
        weight=0.8  # Higher weight means it's more strict about these keywords
    )

    deep_crawl_config = BestFirstCrawlingStrategy(
        max_depth=2,
        url_scorer=scorer, # Use the scorer here!
        max_pages=15
    )

    run_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_config,
        magic=True,
        cache_mode="BYPASS"
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(url="https://www.nvidia.com", config=run_config)
        
        # results is already sorted by the Scorer if you use BestFirst strategy!
        # But let's refine it further with an LLM for "Agentic" decision making.
        
        urls_to_analyze = [res.url for res in results if res.success]
        
        print("\n--- Top 3 URLs Selected by AI ---")
        selected_urls = await select_best_urls_with_llm(urls_to_analyze, user_target_fields)
        
        for url in selected_urls:
            print(f"Action: Scraping {url} for target data...")
            # Now run a full scrape on ONLY these selected URLs
            # final_result = await crawler.arun(url=url, config=run_config)

async def select_best_urls_with_llm(url_list, fields):
    """
    Simulated LLM call to pick the most relevant links from a list.
    You can use OpenAI/Anthropic here to parse the list.
    """
    # Logic: Prompt the LLM with the list of URLs and the fields you need.
    # Ask it to return a JSON list of the top 3 most promising URLs.
    # This is much cheaper than scraping all 20 pages!
    return url_list[:3] # Returning top 3 for this example

if __name__ == "__main__":
    asyncio.run(main())