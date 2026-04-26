import re
from urllib.parse import urlparse, unquote

# Clean data for llm
def clean_for_llm(content: str) -> str:
    """Strip markdown noise before sending to LLM."""
    text = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[#*_`]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 2]
    return "\n".join(lines)

# Extracting links from content
def extract_link_text(link: dict, abs_url: str) -> str:
    """Get meaningful text from a link — fallback to URL path if text is generic."""
    text = re.sub(r'\s+', ' ', link.get("text", "")).strip()
    if not text or text.lower() in ["index.html", "index", ""]:
        parts = [p for p in urlparse(unquote(abs_url)).path.split("/")
                 if p and p != "index.html"]
        text = parts[-2].replace("-", " ").replace("_", " ") if len(parts) >= 2 \
               else parts[-1] if parts else ""
    return text[:60]