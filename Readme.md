# AI Web Scraper

A web scraping tool that takes a URL and a list of fields, then uses AI to extract structured data from the page. The project was built in two phases — first as a visual workflow using n8n, then rewritten as a proper Python backend with a Next.js frontend.

---

## What it does

You give it a URL and tell it what data you want (for example: title, price, rating). It crawls the page, checks if the data is available on the homepage, and if not, it follows relevant links and keeps looking until it finds what it needs. The final output is a structured JSON with the extracted fields.

---

## Project Structure

```javascript
ai-web-scraper/
├── backend/                  # Python + Flask API
│   ├── server.py             # Flask entry point
│   ├── main.py               # Core scrape() function
│   ├── config.py             # Environment variables
│   ├── run.py                # Run scraper standalone
│   └── core/
│       ├── crawler.py        # Crawl4AI + ScrapingBee routing
│       ├── extractor.py      # LLM prompts for data extraction
│       ├── validator.py      # Homepage sufficiency check
│       └── utils.py          # Text cleaning helpers
├── frontend/                 # Next.js UI
│   ├── app/
│   │   ├── page.tsx          # Main UI
│   │   └── globals.css
│   └── components/
│       ├── TagInput.tsx      # URL and field tag inputs
│       ├── OutputCard.tsx    # JSON output display
│       └── FormatUtils.ts    # JSON formatting
└── n8n/
    └── Scraper.json          # Exported n8n workflow
```

---

## Approach 1 — n8n Workflow

The first version was built entirely inside n8n, a no-code automation platform. The idea was to design the agent logic visually before writing any code.

The workflow is triggered by a webhook that accepts a URL and a list of fields. It then passes the URL to Jina AI, which converts the webpage into clean markdown text. A Gemini LLM node reads this content and tries to extract the requested fields directly from the homepage.

If the homepage has enough data (at least 5 items with all fields populated), it returns immediately. If not, another LLM node analyzes the links on the page and picks the top 5 most relevant ones based on URL patterns. The workflow then loops through each link, scrapes it with Jina, validates the content with Gemini, and collects whatever useful data it finds. A wait node between requests prevents rate limiting. At the end, all collected data is merged and returned to the client.

The n8n approach was good for prototyping the logic quickly and seeing the full flow visually. The main limitations were that Jina AI gets blocked by sites like Amazon, JSON parsing between nodes was fragile, and there was no easy way to add retries or fallback logic.

### n8n Workflow Flow

```javascript
Webhook (POST /scrape)
    -> Jina AI (scrape homepage)
    -> Gemini (extract fields from homepage)
    -> Check if homepage is sufficient
        -> Yes: return data
        -> No: extract links
            -> Gemini (pick top 5 relevant links)
            -> Loop through links
                -> Wait (2s)
                -> Jina AI (scrape link)
                -> Gemini (validate and extract)
                -> Store if sufficient
            -> Aggregate and return
```

---

## Approach 2 — Python Backend with Flask and Crawl4AI

The second version replaces every n8n node with Python code. The logic is identical but it is more reliable, easier to debug, and handles edge cases properly.

### Crawling

Instead of Jina AI, the scraper uses Crawl4AI with Playwright underneath. It launches a headless browser, waits for JavaScript to render, applies a pruning filter to remove low-value content (navbars, footers, ads), and returns clean markdown text. For sites that block headless browsers (Amazon, LinkedIn), requests are routed through ScrapingBee which uses residential proxies and handles captchas automatically.

```python
# Normal sites
async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url=url, config=config)
```

### Extraction

The cleaned text is sent to an LLM (Gemini 2.5 Flash via OpenRouter) with a prompt that asks it to return a JSON array of objects, one per item found. The prompt is structured to ask for all items at once rather than field by field, which is more reliable.

### Validation

Before going deeper into links, the code checks if the homepage data is already sufficient. It first does a quick local check (if 5+ items were found with all fields present, no LLM call needed). If the quick check fails, it asks the LLM to validate. This saves unnecessary API calls on pages like books.toscrape.com where the data is immediately available.

### Link following

If the homepage is not sufficient, the LLM picks the most relevant links from the page based on URL patterns. The scraper then visits each one, extracts data, and collects results. A 2 second delay between requests mirrors the wait node from the n8n version.

### Flask API

Flask wraps the scraper in a REST API. The main challenge on Windows was that Playwright requires a ProactorEventLoop while Flask runs on a regular event loop. This was solved by running each scrape in a dedicated thread with its own ProactorEventLoop, completely separate from Flask's thread.

```python
def run_async(coro):
    def thread_target():
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        result_holder["value"] = loop.run_until_complete(coro)
    t = threading.Thread(target=thread_target)
    t.start()
    t.join()
```

### API Endpoints

```javascript
GET  /          — status and available routes
GET  /health    — health check
POST /scrape    — main endpoint

POST /scrape body:
{
  "url": "https://books.toscrape.com",
  "fields": ["title", "price", "rating"]
}
```

---

## Frontend — Next.js

The UI is a single page built with Next.js 14 and Tailwind CSS. It lets you add multiple URLs as tags, define the fields you want to extract, optionally enter a search query, and choose between the local Flask API or the n8n cloud webhook.

When you hit Scrape, it fires parallel requests for each URL using Promise.allSettled, so one failing URL does not block the others. Results appear in a tabbed output card with a fixed-height JSON viewer, a filter/highlight input, copy to clipboard, and JSON download.

The TagInput component commits a tag on Enter, Tab, or comma, and lets you remove tags with Backspace. Both the URL input and the fields input use this same component.

The output card uses usehooks-ts for clipboard access rather than the raw navigator.clipboard API, which simplifies the copy logic to a single line.

### Switching between backends

```javascript
Local API  -> http://localhost:5001/scrape  (Flask + Crawl4AI)
n8n Cloud  -> https://your-n8n.cloud/webhook/scrape  (n8n workflow)
```

Both accept the same request shape so the frontend does not need to change.

---

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
playwright install chromium
python server.py
```

### Frontend

```bash
cd frontend
npm install
```

```bash
npm run dev
```

---

## Requirements

```javascript
# backend/requirements.txt
crawl4ai
openai
beautifulsoup4
httpx
python-dotenv
flask
flask-cors
```

```javascript
# frontend/package.json dependencies
next 14
react 18
tailwindcss 3
usehooks-ts
```

---

## Environment Variables

| Variable | Description |
| --- | --- |
| OPENROUTER_API_KEY | OpenRouter key for Gemini access |
| MODEL | LLM model string (default: google/gemini-2.5-flash) |
| NEXT_PUBLIC_BACKEND_URL | Flask API URL for the frontend |
| NEXT_PUBLIC_N8N_API | n8n webhook URL for the frontend |

---

## Known Limitations

Sites like Amazon block headless browsers regardless of stealth settings. ScrapingBee handles this but costs credits. The LLM extraction is only as good as the page content — if the site renders data entirely in JavaScript after interaction (infinite scroll, click-to-load), Crawl4AI may not capture it without custom JavaScript injection. The n8n workflow has a disconnected response node for the homepage-sufficient path which is a known bug in the exported workflow.

### Current Implementation: The Generalized Approach

To achieve a highly adaptable and "generalized" scraping architecture capable of navigating diverse website structures, this project implements a dual-approach:

* **Crawl4AI:** Leveraging its advanced browser configuration (Stealth Mode, Managed Browsers) and LLM-driven extraction to handle dynamic content and initial bot detection.
* **n8n Automation:** Used for workflow orchestration, URL filtering, and logic-based data processing.

### Challenges: Captcha & Anti-Bot Protection

Standard scraping often encounters friction from dynamic Captchas and sophisticated anti-bot shields (e.g., Cloudflare, Akamai). While the current setup maximizes stealth via fingerprinting, these remain significant hurdles for fully automated systems.

### Future Roadmap: Advanced Bypass & Scaling

To further harden the automation against aggressive IP blocking and rotating protection, the following integrations are considered for future development:

* **ScrapingBee / Specialized APIs:** To offload headless browser management and automated proxy rotation specifically to solve Captchas at scale.
* **Firecrawl / AI Crawlers:** Transitioning toward AI-native crawling engines designed to normalize data from anti-IP rotating websites.

### Why Crawl4AI + n8n?

For this specific project phase, the combination of **Crawl4AI** and **n8n** was selected as the optimal path to create a **Generalized Scraper**. This stack provides the right balance of browser-level control and low-code orchestration to extract useful data from most websites without the high overhead of specialized third-party services.
