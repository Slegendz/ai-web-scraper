# Extract Interactive Elements

# Use a config that only extracts links, inputs, and buttons
# discovery_config = CrawlerRunConfig(
#     only_text=False, 
#     excluded_tags=["p", "span", "footer"], # Ignore text blocks for now
#     include_interactive_elements=True 
# )




# Step B: The "Planning" Prompt
# Send the list of elements to Gemini with this instruction:

# "You are a web automation expert. Given the following HTML elements from [Website URL], identify the CSS selector for the search input and the search submit button. Return only a JSON object: {'input_selector': '...', 'button_selector': '...'}."






# Step C: Execute Dynamic Actions

# Logic to turn AI response into Crawl4AI actions
# ai_selectors = get_selectors_from_gemini(page_elements) 

# actions = ActionChain() \
#     .send_keys(ai_selectors['input_selector'], "Laptop") \
#     .click(ai_selectors['button_selector']) \
#     .wait_for_network_idle()



import os
import asyncio
import json
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, DefaultMarkdownGenerator, PruningContentFilter
from dotenv import load_dotenv

load_dotenv()  

# --- 1. CONFIGURATION & MODELS ---
# Set your API key here or via environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

class SearchElements(BaseModel):
    """Schema for AI to identify web elements"""
    input_selector: str = Field(description="CSS selector for the search text input")
    button_selector: str = Field(description="CSS selector for the search/submit button")

class ExtractedData(BaseModel):
    """Schema for the final structured output"""
    results: List[dict] = Field(description="List of items found with the requested fields")

# --- 2. AI BRAIN FUNCTIONS ---

async def ai_find_selectors(url: str, html: str) -> SearchElements:
    """Stage 1: AI looks at the page to find the search bar."""
    print(f"🧠 AI is analyzing {url} to find the search bar...")
    
    prompt = f"""
    Below is a simplified HTML snippet from {url}. 
    Find the CSS selector for the search input field and the search button.
    Focus on elements like <input type='text'>, <input type='search'>, and <button> or <input type='submit'>.
    
    HTML:
    {html[:8000]}  # Sending first 8k chars of HTML
    """
    
    response = client.models.generate_content(
        model="gemini-flash-content",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SearchElements
        )
    )
    return response.parsed

async def ai_extract_structured_data(markdown: str, fields: List[str]) -> ExtractedData:
    """Stage 3: AI turns raw markdown into a clean JSON list."""
    print("🧠 AI is transforming markdown into structured JSON...")
    
    prompt = f"""
    Extract the following fields from the markdown content: {', '.join(fields)}.
    If a field is missing for an item, use null.
    
    CONTENT:
    {markdown}
    """
    
    response = client.models.generate_content(
        model="gemini-3-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedData
        )
    )
    return response.parsed

# Setup Browser - headless=False is better for debugging/demos
browser_cfg = BrowserConfig(
    browser_type="chromium",
    headless=False,           # CRITICAL: Amazon blocks headless browsers easily
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    enable_stealth= True,
)


def get_config():
    md_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.4, 
            threshold_type="fixed",
        ),
        options={
            "ignore_links": True,
            "ignore_images": True,
            "include_selectors": True
        }
    )

    return CrawlerRunConfig(
        css_selector="input[type='text'], input[type='search'], button, input[type='submit'], form, label",
        only_text=False, 
        word_count_threshold=0, 
        
        # 4. Standard noise reduction
        remove_overlay_elements=True,
        markdown_generator=md_generator,
        magic=True,
        wait_for="input"
    )

# --- 3. THE MAIN EXECUTION ENGINE ---
async def run_autonomous_agent(target_url: str, search_query: str, data_fields: List[str]):
    config = get_config()
        
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        home_result = await crawler.arun(url=target_url, config=config)
        
        print(home_result)

        # Assume your AI find_selectors logic returns the CSS selectors
        selectors = await ai_find_selectors(target_url, home_result.html)

        # STEP 2 & 3: Perform Search & Scrape (The New Way)
        # Instead of ActionChain, we pass the interaction as JavaScript
        scrape_cfg = CrawlerRunConfig(
            # This replaces the ActionChain logic entirely
            js_code=[
                f"document.querySelector('{selectors.input_selector}').value = '{search_query}';",
                f"document.querySelector('{selectors.button_selector}').click();"
            ],
            wait_for=f"css={selectors.input_selector}", # Wait for the page to react
            word_count_threshold=10
        )

        print(f"⌨️ Performing search for '{search_query}'...")
        search_result = await crawler.arun(url=target_url, config=scrape_cfg)
        
        # STEP 4: AI Extraction
        raw_markdown = search_result.markdown_v2.fit_markdown or search_result.markdown_v2.raw_markdown
        structured_json = await ai_extract_structured_data(raw_markdown, data_fields)
        
        return structured_json

# --- 4. START THE AGENT ---

if __name__ == "__main__":
    # USER INPUTS
    TARGET = "https://www.flipkart.in"
    QUERY = "gaming laptops under 80000"
    FIELDS = ["Product Name", "Price", "Rating", "Review Count"]

    if not GOOGLE_API_KEY:
        print("❌ ERROR: Please set your GOOGLE_API_KEY in the script.")
    else:
        results = asyncio.run(run_autonomous_agent(TARGET, QUERY, FIELDS))
        
        print("\n" + "="*50)
        print("✨ FINAL STRUCTURED DATA ✨")
        print("="*50)
        print(json.dumps(results.model_dump(), indent=2))