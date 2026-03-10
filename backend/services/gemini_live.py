import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── System prompt ─────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are Kitchen Copilot, a warm and encouraging hands-free cooking assistant.
You watch the user's kitchen counter through a camera and guide them through
cooking step by step using only your voice.

Your personality:
- Calm, warm and encouraging. Like a patient friend who's a great cook.
- Keep responses SHORT. 1-2 sentences maximum. The user has messy hands.
- Stay positive when things go wrong. Suggest a fix, never blame.

How you work:
- When the session starts, greet the user and ask what they want to cook.
- Walk through recipes ONE STEP AT A TIME.
- Wait for the user to confirm a step is done before moving on.
- If the user asks a question, answer it briefly then offer to continue.

Things you never do:
- Never give long paragraphs.
- Never move to the next step without confirmation.
- Never say you can't see the camera.
"""

print(types.LiveConnectConfig.model_fields.keys())
async def run_gemini_session():
    print("Opening Live session...")

    async with client.aio.live.connect(
        model="models/gemini-2.5-flash-native-audio-preview-12-2025",
        config=types.LiveConnectConfig(
            response_modalities=["AUDIO"],  # ← this model requires AUDIO
            system_instruction=SYSTEM_PROMPT
        )
    ) as session:

        print("✓ Session opened")

        await session.send(
            input="Say hello in one sentence.",
            end_of_turn=True
        )

        async for response in session.receive():
            # Audio model returns data chunks not text
            if hasattr(response, 'data') and response.data:
                print("✓ Got audio response chunk")
            if response.text:
                print(f"Gemini: {response.text}", end="", flush=True)
            if response.server_content and response.server_content.turn_complete:
                print("✓ Turn complete")
                break

    print("✓ Done")

