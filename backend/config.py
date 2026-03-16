import os

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID", "kitchen-copilot-proj"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "(default)")
REGION = os.environ.get("REGION", "us-central1")
