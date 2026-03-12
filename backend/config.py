import os

PROJECT_ID = os.environ.get("PROJECT_ID", "project-0b207fe2-c7dd-4d8f-a5c")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
FIRESTORE_DATABASE = os.environ.get("FIRESTORE_DATABASE", "(default)")
REGION = os.environ.get("REGION", "us-central1")
