import json
import re
from openai import OpenAI
from config import OPENROUTER_API_KEY, MODEL
from src.utils import clean_for_llm

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)


# LLM Reasoning
def ask_llm(prompt: str):
    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
    )
    raw = res.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {}


# Extract homepage data
def extract_homepage_data(content: str, fields: list) -> list:
    clean = clean_for_llm(content)
    result = ask_llm(
        f"""
You are a data extraction specialist.

Target Fields: {fields}
Page Content:
{clean}

Extract ALL items containing the target fields.
Return a JSON array — one object per item.

Example for ["title","price","rating"]:
[
  {{"title": "Book A", "price": "£12.99", "rating": "4"}},
  {{"title": "Book B", "price": "£8.50",  "rating": "3"}}
]

Return ONLY the JSON array. No explanation, no markdown.
"""
    )

    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                return v
    return []


# Pick best links 
def pick_best_links(links: list, fields: list) -> list:
    result = ask_llm(
        f"""
Target Fields: {fields}
Candidate URLs: {json.dumps([l["url"] for l in links])}

Select top 5 URLs most likely to contain the target fields.
Prefer: /product/, /catalogue/, /item/, /category/, /page/

Return ONLY:
{{"recommended_links": ["url1", "url2"]}}
"""
    )
    return result.get("recommended_links", [])[:5]


# Validate scraped content
def validate_page(content: str, url: str, fields: list) -> dict:
    clean = clean_for_llm(content)
    return ask_llm(
        f"""
Target Fields: {fields}
URL: {url}
Content: {clean}

Extract the fields if present. Return ONLY:
{{
  "is_sufficient": true or false,
  "extracted_data": [{{"field1": "value1"}}] or null
}}
"""
    )
