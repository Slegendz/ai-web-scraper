import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL", "google/gemini-2.5-flash")

SKIP_EXT = {".png",".jpg",".jpeg",".gif",".webp",".svg",".ico",".pdf",".css",".js"}