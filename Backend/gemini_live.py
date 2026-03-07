import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents= "why is the sky blue?"
)
print(response.text)




