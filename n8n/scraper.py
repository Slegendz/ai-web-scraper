import requests
import json

def trigger_n8n_scraper(target_url, fields_list):
    WEBHOOK_URL = "https://slegendz.app.n8n.cloud/webhook-test/scrape"
    
    payload = {
        "parameters": {
            "url": target_url,
            "fields": fields_list,
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    print(f"Sending request to n8n for URL: {target_url}...")
    
    try:
        response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 200:
            print("Successfully triggered n8n workflow.")
            print("Response:", response.text)
        else:
            print(f"Failed to trigger n8n. Status Code: {response.status_code}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    trigger_n8n_scraper(
        target_url="https://books.toscrape.com/", 
        fields_list=["Book name", "Price", "Availability"]
    )