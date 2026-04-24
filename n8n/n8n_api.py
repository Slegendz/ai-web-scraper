"""
n8n_api.py  —  FastAPI Bridge for n8n
=======================================
Starts a local HTTP server that n8n calls via an HTTP Request node.

How to run:
    cd c:\\Users\\SachinNegi\\Downloads\\ai-web-scraper
    python -m uvicorn n8n.n8n_api:app --host 0.0.0.0 --port 5678 --reload

Then in n8n, point an HTTP Request node to:
    POST  http://localhost:5678/api/scrape

If n8n is on the cloud (n8n.cloud), expose this server first:
    ngrok http 5678
    → then use the ngrok URL in n8n

API endpoints:
    GET  /api/health         — Check if the server is running
    POST /api/scrape         — Full AI scrape (deep, follows links)
    POST /api/quick-scrape   — Fast single-page scrape only
    GET  /docs               — Interactive API docs (Swagger UI)
"""

import asyncio
import os
import sys
import time

import nest_asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Windows asyncio fix (required for uvicorn on Windows)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
nest_asyncio.apply()

# Add project root to path so we can import src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.smart_scraper import run_scraper


# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Web Scraper API",
    description=(
        "Intelligent web scraper powered by crawl4ai and Gemini. "
        "Handles dynamic sites, captchas, and search bars. Built for n8n."
    ),
    version="2.0.0",
)

# Allow all origins so n8n and the frontend can both call this freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request & response models ──────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url:          str       = Field(...,  description="Website URL to scrape")
    fields:       list[str] = Field(...,  description="Data fields to extract, e.g. ['Title', 'Price']")
    search_query: str | None = Field(None, description="Optional: type this into the site's search bar first")
    max_pages:    int       = Field(6, ge=1, le=30, description="Max pages to visit (1–30)")


class QuickScrapeRequest(BaseModel):
    url:          str       = Field(...,  description="Website URL to scrape")
    fields:       list[str] = Field(...,  description="Data fields to extract")
    search_query: str | None = Field(None, description="Optional search query")


class ScrapeResponse(BaseModel):
    seed_url:      str
    fields:        list[str]
    records:       list[dict]     # Each dict maps field name → extracted value
    total_records: int
    pages_visited: int
    summary:       str            # Plain-English AI summary
    errors:        list[str]
    elapsed_seconds: float


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Quick check that the server is alive. n8n can poll this before scraping."""
    return {"status": "ok", "message": "AI Scraper is running"}


@app.post("/api/scrape", response_model=ScrapeResponse)
async def deep_scrape(req: ScrapeRequest):
    """
    Full AI scrape — opens the page, optionally searches, extracts data,
    follows the best follow-up links, and returns a structured result + summary.

    This is the main endpoint for n8n.
    """
    t0 = time.time()
    try:
        result = await run_scraper(
            url=req.url,
            fields=req.fields,
            search_query=req.search_query,
            max_pages=req.max_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ScrapeResponse(
        seed_url=result.seed_url,
        fields=result.fields,
        records=result.records,
        total_records=len(result.records),
        pages_visited=result.pages_visited,
        summary=result.summary,
        errors=result.errors,
        elapsed_seconds=round(time.time() - t0, 2),
    )


@app.post("/api/quick-scrape", response_model=ScrapeResponse)
async def quick_scrape(req: QuickScrapeRequest):
    """
    Single-page only scrape (no link following). Much faster.
    Good for testing, or when you know the data is all on one page.
    """
    t0 = time.time()
    try:
        result = await run_scraper(
            url=req.url,
            fields=req.fields,
            search_query=req.search_query,
            max_pages=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ScrapeResponse(
        seed_url=result.seed_url,
        fields=result.fields,
        records=result.records,
        total_records=len(result.records),
        pages_visited=result.pages_visited,
        summary=result.summary,
        errors=result.errors,
        elapsed_seconds=round(time.time() - t0, 2),
    )


# ── Run directly ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n  AI Scraper API starting on http://localhost:5678")
    print("  API docs at:  http://localhost:5678/docs\n")
    uvicorn.run("n8n_api:app", host="0.0.0.0", port=5678, reload=True)
