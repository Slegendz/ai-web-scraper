import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from main import scrape

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return jsonify({
        "status": "running",
        "routes": {
            "POST /scrape": {"body": {"url": "string", "fields": ["list"]}},
        }
    })


@app.route("/scrape", methods=["POST"])
def scrape_endpoint():
    data = request.json or {}
    url = data.get("url", "").strip()
    fields = data.get("fields", [])

    print(f"POST /scrape | url={url} | fields={fields}")

    if not url:
        return jsonify({"success": False, "error": "url is required"}), 400
    if not fields:
        return jsonify({"success": False, "error": "fields is required"}), 400

    try:
        result = asyncio.run(scrape(url=url, fields=fields))
        return jsonify(result), 200

    except Exception as e:
        print(f"Scrape failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("AI Scraper Flask API")
    print("=" * 40)

    app.run(host="0.0.0.0", port=5001, debug=True)