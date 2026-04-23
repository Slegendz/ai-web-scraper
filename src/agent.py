# import os
# from pydantic import BaseModel, Field
# from typing import List, Optional
# from google import genai
# from google.genai import types

# # 1. Define what you want to find (The "Required Data Fields")
# class CompanyInfo(BaseModel):
#     company_name: str = Field(description="The official name of the company")
#     industry: str = Field(description="The primary industry or sector")
#     revenue: Optional[str] = Field(description="Annual revenue if mentioned")
#     hq_location: str = Field(description="Headquarters city and country")
#     key_products: List[str] = Field(description="List of main products or services")

# def extract_company_data(markdown_content: str):
#     client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
#     prompt = f"""
#     Extract the following information from the provided markdown text. 
#     If a field is not found, return null.
    
#     CONTENT:
#     {markdown_content}
#     """

#     # 3. Call Gemini with 'response_mime_type' for forced JSON
#     response = client.models.generate_content(
#         model="gemini-3-flash",
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             response_mime_type="application/json",
#             response_schema=CompanyInfo, 
#         ),
#     )
    
#     return response.parsed  # This returns a Python object (CompanyInfo)




# from google import genai
# from google.genai import types
# import json, re

# client = genai.Client(api_key="")

# def extract_fields(markdown: str, fields: list[str], url: str) -> dict:
#     fields_str = "\n".join(f"- {f}" for f in fields)
#     prompt = f"""
# You are a precise data extractor. From the webpage content below, extract ONLY these fields:
# {fields_str}

# Return a JSON object with field names as keys and extracted values as values.
# If a field is not found, use null.
# Return ONLY valid JSON, no explanation, no markdown fences.

# Source URL: {url}
# Content:
# {markdown[:6000]}
# """
#     response = client.models.generate_content(
#         model="gemini-1.5-flash",
#         contents=prompt
#     )
#     raw = response.text.strip()
#     raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
#     try:
#         return json.loads(raw)
#     except json.JSONDecodeError:
#         return {f: None for f in fields}


# def summarize_results(all_data: list[dict], fields: list[str]) -> str:
#     prompt = f"""
# Below is structured data extracted from multiple pages of a website.
# Fields of interest: {', '.join(fields)}

# Data:
# {json.dumps(all_data, indent=2)[:8000]}

# Write a concise, human-readable summary of the key findings.
# """
#     response = client.models.generate_content(
#         model="gemini-2.0-flash",
#         contents=prompt
#     )
#     return response.text


from openai import OpenAI
import json, re

client = OpenAI(api_key="")

def extract_fields(markdown: str, fields: list[str], url: str) -> dict:
    fields_str = "\n".join(f"- {f}" for f in fields)
    prompt = f"""
Extract ONLY these fields from the content below:
{fields_str}

Return ONLY valid JSON, no explanation, no markdown fences.
If a field is not found, use null.

Source URL: {url}
Content:
{markdown[:6000]}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {f: None for f in fields}


def summarize_results(all_data: list[dict], fields: list[str]) -> str:
    prompt = f"""
Summarize the key findings from this extracted website data.
Fields: {', '.join(fields)}
Data: {json.dumps(all_data, indent=2)[:8000]}
Write a concise, human-readable summary.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content