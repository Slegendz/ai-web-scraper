from flask import Flask, render_template, request, jsonify
import asyncio, sys, nest_asyncio
from src.scraper import crawl_site
from src.agent import extract_fields, summarize_results

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

nest_asyncio.apply()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    url = data.get("url")
    fields = [f.strip() for f in data.get("fields", "").splitlines() if f.strip()]
    max_pages = int(data.get("max_pages", 3))

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        pages = loop.run_until_complete(crawl_site(url, max_pages=max_pages))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    all_extracted = []
    for page in pages:
        extracted = extract_fields(page["markdown"], fields, page["url"])
        extracted["_source_url"] = page["url"]
        all_extracted.append(extracted)

    # summary = summarize_results(all_extracted, fields)
    # return jsonify({"results": all_extracted, "summary": summary})
    return

if __name__ == "__main__":
    app.run(debug=False)