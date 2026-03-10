import builtins

# 🔥 THE INVINCIBLE WINDOWS CONSOLE SHIELD 🔥
# The Gemini SDK has hardcoded unicode emojis (✓) that it prints asynchronously on connection.
# Windows Uvicorn crashes when it prints these. We patch 'builtins.print' to swallow encoding errors.
_original_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        _original_print(*args, **kwargs)
    except UnicodeEncodeError:
        pass  # Just swallow it! Let the server live!
builtins.print = safe_print

import os
import json
import asyncio
import traceback
import logging
import base64 # Added from user's example, though not explicitly used in original code

from fastapi import WebSocket, WebSocketDisconnect
from dotenv import load_dotenv # Corrected from user's example `genaid_dotenv`
from google import genai
from google.genai import types

from backend.services.tool import search_recipes_tool, timer_tool, handle_tool_call

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
- If you need to set a timer, use the tool. If the user asks about a timer, use the tool.
- If the user asks for recipes based on ingredients, use the tool.

Things you never do:
- Never give long paragraphs.
- Never move to the next step without confirmation.
- Never say you can't see the camera if you can see it. If you can't, ask the user to adjust the camera.
"""


async def get_active_state() -> dict:
    """Mock for now: grab active state to send to frontend."""
    from backend.services.timer import get_timers
    return {
        "timers": get_timers()
    }


async def run_gemini_session(websocket: WebSocket, session_id: str):
    """
    Main real-time bridge. Connects to Gemini Live API and multiplexes
    the FastAPI WebSocket traffic (binary/text).
    """
    import contextlib
    import sys
    import io

    print(f"[{session_id}] Opening Gemini Live session...")

    try:
        # The Gemini SDK prints a checkmark when it connects that crashes Windows consoles. 
        # We redirect stdout to a dummy buffer just for the connect phase to swallow it.
        dummy_stdout = io.StringIO()
        with contextlib.redirect_stdout(dummy_stdout):
            connection = client.aio.live.connect(
                model="models/gemini-2.5-flash-native-audio-preview-12-2025",
                config=types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    system_instruction=types.Content(parts=[types.Part.from_text(text=SYSTEM_PROMPT)]),
                    tools=[search_recipes_tool, timer_tool]
                )
            )
        
        async with connection as session:

            print(f"[{session_id}] OK Session opened")

            # Kick off the conversation
            await session.send(
                input="Say hello to me in one short welcoming sentence.",
                end_of_turn=True
            )

            # Inbound loop: Client -> FastAPI -> Gemini
            async def receive_from_client():
                while True:
                    try:
                        data = await websocket.receive()
                        if "bytes" in data:
                            raw_bytes = data["bytes"]
                            if len(raw_bytes) > 0:
                                header = raw_bytes[0]
                                payload = raw_bytes[1:]
                                
                                if header == 0x00:
                                    # Audio PCM
                                    await session.send_realtime_input(
                                        audio=types.Blob(data=payload, mime_type="audio/pcm;rate=16000")
                                    )
                                elif header == 0x01:
                                    # User's API Key currently only supports the Audio-Only Preview model.
                                    # Sending video frames causes a 1007 Invalid Payload crash. 
                                    # We silently drop the camera frames until their account gains Multimodal Video access.
                                    pass
                        elif "text" in data:
                            pass
                    except WebSocketDisconnect:
                        print(f"[{session_id}] Client disconnected inside receive loop.")
                        break
                    except Exception as e:
                        print(f"[{session_id}] Client receive error: {e}")

            # Outbound loop: Gemini -> FastAPI -> Client
            async def receive_from_gemini():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content is not None:
                            # 1. Handle Audio output
                            if server_content.model_turn is not None:
                                for part in server_content.model_turn.parts:
                                    if part.inline_data:
                                        # Send raw PCM audio directly to frontend WebSocket
                                        try:
                                            # Debug log every 50th chunk 
                                            # (approx 1 per second) to keep console clean
                                            if not hasattr(session, '_debug_audio_count'):
                                                session._debug_audio_count = 0
                                            session._debug_audio_count += 1
                                            if session._debug_audio_count % 50 == 1:
                                                print(f"[{session_id}] Gemini sent {len(part.inline_data.data)} bytes audio (x{session._debug_audio_count})")
                                            
                                            await websocket.send_bytes(part.inline_data.data)
                                        except Exception as e:
                                            print(f"[{session_id}] Error sending audio to client: {e}")
                                            return

                            # 2. Handle Tool Calls
                            if server_content.model_turn is not None:
                                for part in server_content.model_turn.parts:
                                    if part.executable_code or part.code_execution_result:
                                        pass # code execution not needed for now
                                    if part.function_call:
                                        tool_name = part.function_call.name
                                        tool_args = part.function_call.args
                                        print(f"[{session_id}] Agent called tool: {tool_name}")
                                        
                                        # Execute the tool
                                        result_dict = await handle_tool_call(tool_name, tool_args)
                                        
                                        # Send result back to Gemini
                                        await session.send(
                                            input=[types.Part.from_function_response(
                                                name=tool_name,
                                                response=result_dict
                                            )]
                                        )
                                        
                                        # Broadcast state to frontend
                                        state = await get_active_state()
                                        await websocket.send_text(json.dumps(state))

                        # Handle interruptions (if Gemini starts a new turn, we could tell frontend to clear audio buffer)
                        if response.server_content and response.server_content.interrupted:
                            print(f"[{session_id}] Gemini interrupted response!")

                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"[{session_id}] Gemini receive error: {e}")
                    traceback.print_exc()

            # Run both loops concurrently
            client_task = asyncio.create_task(receive_from_client())
            gemini_task = asyncio.create_task(receive_from_gemini())

            done, pending = await asyncio.wait(
                [client_task, gemini_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()

    except Exception as e:
        print(f"[{session_id}] Critical session error: {e}")
        traceback.print_exc()
        raise e
