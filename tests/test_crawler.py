# import asyncio
# from crawl4ai import AsyncWebCrawler
# from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

# async def main():
#     browser_config = BrowserConfig() 
#     run_config = CrawlerRunConfig()

#     async with AsyncWebCrawler(config=browser_config) as crawler:
#         result = await crawler.arun(
#             url="https://www.scrapethissite.com/pages/simple/",
#             config=run_config
#         )
#         print(result.markdown)

#         if result.success:
#             # markdown_content = result.markdown (For getting the markdown content)
#             markdown_content = result.markdown.raw_markdown
            
#             with open("scraped.md", "w", encoding="utf-8") as f:
#                 f.write(markdown_content)
#             print("Markdown file created successfully!")
#         else:
#             print(f"Crawl failed: {result.error_message}")


# if __name__ == "__main__":
#     asyncio.run(main())


# BFS Deep Crawl Stratergy

import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    # 1. Defining patterns to prioritize finding the right pages
    # This acts like a "GPS" for the crawler
    relevant_patterns = [
        r".*/about.*", 
        r".*/investor.*", 
        r".*/products.*", 
        r".*/financials.*"
    ]

    url_filter = URLPatternFilter(patterns=["*investor*", "*financials*"])

    # Plug the patterns into the strategy
    deep_crawl_config = BFSDeepCrawlStrategy(
        max_depth=2,
        include_external=False,
        # It tells the crawler: "Only follow links that match these regex patterns"
        filter_chain=FilterChain([url_filter]),
        max_pages=30
    )


    run_config = CrawlerRunConfig(
        deep_crawl_strategy=deep_crawl_config,
        # 1. Bypass the heavy Markdown conversion to stay fast
        markdown_generator=DefaultMarkdownGenerator(content_filter=None), 
        # 2. You can also use word_count_threshold to ignore body text entirely
        word_count_threshold=0,
        magic=True,            # Bypass basic bot detection
        cache_mode="BYPASS"
    )

    async with AsyncWebCrawler() as crawler:
        # Starting from the home page
        result = await crawler.arun(
            url="https://www.nvidia.com", 
            config=run_config
        )
        
        # 'result' will now contain a list of pages crawled

        # if result.success:
        #     print(f"Successfully crawled {len(result.deep_crawl_results)} pages.")
        #     for sub_page in result.deep_crawl_results:
        #         print(f"Found and Scraped: {sub_page.url}")
                # You can now pass this sub_page.markdown to your RAG pipeline
        
        # with open("companies_links.txt", "w", encoding="utf-8") as f:
        #         for res in result.deep_crawl_results: 
        #             f.write(res.url + '\n')

        if result:
            print(f"Successfully crawled {len(result)} pages.")
            
            for res in result:
                if res.success:
                    # Accessing the URL and the markdown for each page
                    print(f"Target Acquired: {res.url}")
                else:
                    print(f"Failed to crawl {res.url}: {res.error_message}")
        else:
            print("No pages were crawled.")
            
if __name__ == "__main__":
    asyncio.run(main())