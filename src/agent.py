import os
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types

# 1. Define what you want to find (The "Required Data Fields")
class CompanyInfo(BaseModel):
    company_name: str = Field(description="The official name of the company")
    industry: str = Field(description="The primary industry or sector")
    revenue: Optional[str] = Field(description="Annual revenue if mentioned")
    hq_location: str = Field(description="Headquarters city and country")
    key_products: List[str] = Field(description="List of main products or services")

def extract_company_data(markdown_content: str):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    prompt = f"""
    Extract the following information from the provided markdown text. 
    If a field is not found, return null.
    
    CONTENT:
    {markdown_content}
    """

    # 3. Call Gemini with 'response_mime_type' for forced JSON
    response = client.models.generate_content(
        model="gemini-3-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CompanyInfo, 
        ),
    )
    
    return response.parsed  # This returns a Python object (CompanyInfo)