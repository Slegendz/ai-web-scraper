import openai

def extract_data_with_llm(markdown_content):
    prompt = f"""
    Extract the following information from the markdown below into a JSON format:
    - Product Name
    - Price
    - Rating
    
    Markdown:
    {markdown_content}
    """
    # Use your preferred LLM here
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    return response.choices[0].message.content