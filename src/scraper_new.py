from pydantic import BaseModel, Field
from typing import Optional

class GeneralizedProduct(BaseModel):
    name: str = Field(..., description="The full, untruncated title of the product.")
    price: str = Field(..., description="The current price including currency.")
    availability: str = Field(..., description="Stock status like 'In Stock', 'Out of Stock', or 'Only X left'.")
    rating: Optional[str] = Field(None, description="The star rating or review count.")
    image_url: Optional[str] = Field(None, description="The primary image URL for the product.")


import os
from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy

# --- BROWSER CONFIGURATION (The "Stealth" Shield) ---
def get_browser_config():
    return BrowserConfig(
        headless=True,
        enable_stealth=True,          # Bypasses basic bot detection
        use_managed_browser=True,     # Necessary for Amazon/Protected sites
        user_agent_mode="random",     # Rotates your digital fingerprint
        # magic_browser=True,         # Uncomment if still getting blocked
    )

# --- CRAWLER RUN CONFIGURATION (The "Brain") ---
def get_run_config():
    # 1. Setup the LLM Strategy for generalization
    # This replaces hardcoded CSS/Xpath selectors
    extraction_strategy = LLMExtractionStrategy(
        provider="openai/gpt-4o",      # Or "gemini/gemini-1.5-pro"
        api_token=os.getenv("OPENAI_API_KEY"),
        schema=GeneralizedProduct.schema(),
        extraction_type="schema",
        instruction=(
            "Extract all products from the list. "
            "For names, look at 'title' or 'aria-label' attributes to get the FULL name. "
            "Clean the price and availability fields of any UI artifacts."
        )
    )

    return CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        cache_mode=CacheMode.BYPASS,
        
        # --- Handling Dynamic Elements ---
        wait_until="networkidle",      # Wait for prices to load via JS
        page_timeout=60000,            # 60s for slow-loading dynamic pages
        remove_overlay_elements=True,  # Clears popups/banners that block data
        
        # --- Anti-Bot & Stability ---
        delay_before_scraping=2,       # Human-like delay
        # If Amazon blocks, try changing scan_mode to "deep"
    )