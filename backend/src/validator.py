import json
from src.extractor import ask_llm


def check_homepage_sufficient(extracted: list, fields: list) -> dict:
    """Step 2 — Check if extracted homepage data satisfies the fields."""

    # Quick check without LLM call
    if isinstance(extracted, list) and len(extracted) >= 5:
        sample = extracted[:3]
        if all(all(f in item for f in fields) for item in sample):
            return {
                "homepage_sufficient": True,
                "reasoning": f"{len(extracted)} items with all fields found"
            }

    return ask_llm(f"""
Requested Fields: {fields}
Extracted Data (sample): {json.dumps(extracted[:5], indent=2)}
Total items: {len(extracted)}

Is this sufficient? Rules: 5+ items, all fields present with real values.

Return ONLY:
{{"homepage_sufficient": true or false, "reasoning": "brief explanation"}}
""")