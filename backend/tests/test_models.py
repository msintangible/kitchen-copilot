import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    api_key=os.environ['GEMINI_API_KEY'],
    http_options={'api_version': 'v1alpha'}
)

async def test_models():
    models = ['models/gemini-2.5-flash', 'models/gemini-2.5-pro', 'models/gemini-2.0-flash', 'models/gemini-2.0-flash-001', 'models/gemini-2.0-flash-lite-001', 'models/gemini-2.0-flash-lite', 'models/gemini-2.5-flash-preview-tts', 'models/gemini-2.5-pro-preview-tts', 'models/gemini-2.5-flash-lite', 'models/gemini-2.5-flash-image', 'models/gemini-2.5-flash-lite-preview-09-2025', 'models/gemini-2.5-computer-use-preview-10-2025', 'models/gemini-2.5-flash-native-audio-latest', 'models/gemini-2.5-flash-native-audio-preview-09-2025', 'models/gemini-2.5-flash-native-audio-preview-12-2025', 'gemini-2.0-flash-exp']
    
    for m in models:
        print(f"Testing {m}...")
        try:
            async with client.aio.live.connect(model=m, config=types.LiveConnectConfig()) as session:
                print(f"SUCCESS: {m} supports Live API!")
        except Exception as e:
            msg = str(e)
            if "1008" in msg:
                print(f"  -> Failed (1008 Unsupported)")
            elif "404" in msg:
                print(f"  -> Failed (404 Not Found)")
            else:
                print(f"  -> Failed: {msg[:100]}")

if __name__ == "__main__":
    asyncio.run(test_models())
