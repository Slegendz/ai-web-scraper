# Ai web scraper

ai-web-scraper/
├── .env                  # API Keys (GOOGLE_API_KEY, etc.)
├── .gitignore            # Ignore __pycache__, .env, and venv
├── requirements.txt      # List of dependencies
├── README.md             # Project documentation
│
├── app.py                # MAIN ENTRY: The Streamlit UI
│
├── src/                  # Core logic folder
│   ├── __init__.py
│   ├── crawler.py        # Crawl4AI logic (navigation & markdown extraction)
│   ├── agent.py          # Google AI Agent (LLM) logic for field mapping
│   ├── processor.py      # Data cleaning and CSV/Excel export logic
│   └── utils.py          # Helper functions (logging, URL validation)
│
├── assets/               # UI assets (images, custom CSS)
│   └── style.css
│
└── tests/                # Unit tests for crawler and agent
    ├── test_crawler.py
    └── test_agent.py