import builtins

# 🔥 THE INVINCIBLE WINDOWS CONSOLE SHIELD 🔥
# The Gemini SDK has hardcoded unicode emojis (✓) that it prints asynchronously on connection.
# Windows Uvicorn crashes when it prints these. We patch 'builtins.print' to swallow encoding errors.
_original_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        msg = " ".join(str(a) for a in args)
        with open("backend_debug.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        _original_print(*args, **kwargs)
    except Exception:
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

from services.tool import search_recipes_tool, search_recipe_by_name_tool, timer_tool, ui_command_tool, handle_tool_call, pop_pending_ui_commands, reset_backend_state

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
- When the session starts, greet the user briefly and ask what they'd like to cook or what ingredients they have.
- If the user says EXACTLY what dish they want to cook (e.g. "make me fried rice", "I want chicken bolognese"),
  call the search_recipe_by_name tool immediately. This fetches the standard recipe and shows it directly on screen — no picker.
- If the user mentions ingredients they have (e.g. "I have eggs, milk and oats"),
  call the search_recipes tool. This finds recipes that match their ingredients and shows a picker.
- After search_recipes returns, the user sees a visual popup with recipe cards.
  DO NOT read out all the recipe details. Just say: "I found 3 recipes! Take a look and tell me which one you'd like to try."
- When the user tells you which recipe they want from the picker, IMMEDIATELY call the ui_command tool
  with action='select_recipe' and recipe_id set to the chosen recipe's Spoonacular ID.
- After search_recipe_by_name or select_recipe, the recipe steps appear on screen automatically.
  Then walk through the recipe ONE STEP AT A TIME. Read each step aloud briefly.
- Wait for the user to say "done" or "next" before moving on.
- If a step involves timing (e.g. "bake for 20 minutes"), proactively ask if they want a timer set.

Voice commands you must handle via the ui_command tool:
- "Show recipe" or "open sidebar" → call ui_command with action='show_sidebar'
- "Hide recipe" or "close sidebar" → call ui_command with action='hide_sidebar'  
- "Mute" or "unmute" → call ui_command with action='toggle_mute'
- "Stop session", "end session", or "goodbye" → call ui_command with action='stop_session'
- "Done", "next step", "I finished this step", "step X is done" → call ui_command with action='step_done'. If the user mentions a specific step number, include step_number (1-indexed). Otherwise omit step_number to advance to the next step automatically.
- "Show my other timer" or "Bring pasta timer to front" → call ui_command with action='focus_timer' and timer_id='the_timer_id'

IMPORTANT: When the user says anything that indicates they finished a step (like "done", "next", "I'm done", "finished", "completed", "got it"), you MUST call ui_command with action='step_done'. Do NOT just verbally acknowledge — you must also call the tool.

Things you never do:
- Never give long paragraphs or list all recipe details verbally (the screen shows them).
- Never move to the next step without confirmation.
- Never say you can't see the camera if you can see it.
"""


async def get_active_state() -> dict:
    """Mock for now: grab active state to send to frontend."""
    from services.timer import get_timers
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
    reset_backend_state()

    try:
        # The Gemini SDK prints a checkmark when it connects that crashes Windows consoles. 
        # We redirect stdout to a dummy buffer just for the connect phase to swallow it.
        dummy_stdout = io.StringIO()
        with contextlib.redirect_stdout(dummy_stdout):
            connection = client.aio.live.connect(
                model="models/gemini-2.5-flash-native-audio-latest",
                config=types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    system_instruction=types.Content(parts=[types.Part.from_text(text=SYSTEM_PROMPT)]),
                    tools=[search_recipes_tool, search_recipe_by_name_tool, timer_tool, ui_command_tool]
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
                        
                        # Check for disconnect message
                        if data.get("type") == "websocket.disconnect":
                            print(f"[{session_id}] Client sent disconnect frame.")
                            break
                        
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
                                    # Video JPEG Frame
                                    print(f"[{session_id}] Sending video frame ({len(payload)} bytes)...")
                                    try:
                                        await session.send_realtime_input(
                                            video=types.Blob(data=payload, mime_type="image/jpeg")
                                        )
                                        print(f"[{session_id}] Video frame sent OK")
                                    except Exception as ve:
                                        print(f"[{session_id}] VIDEO SEND ERROR: {ve}")
                                        traceback.print_exc()
                        elif "text" in data:
                            text_data = data["text"]
                            print(f"[{session_id}] 📥 Received text payload from client: {text_data[:50]}...")
                            try:
                                json_payload = json.loads(text_data)
                                if "clientContent" in json_payload:
                                    # Passing text prompt directly to Gemini
                                    print(f"[{session_id}] 📤 Sending text prompt to Gemini...")
                                    await session.send(input=text_data, end_of_turn=True)
                            except Exception as text_e:
                                print(f"[{session_id}] Error parsing text from client: {text_e}")
                    except WebSocketDisconnect:
                        print(f"[{session_id}] Client disconnected (WebSocketDisconnect).")
                        break
                    except RuntimeError as re:
                        # "Cannot call receive once disconnect" — normal cleanup
                        print(f"[{session_id}] Client WebSocket closed: {re}")
                        break
                    except Exception as e:
                        print(f"[{session_id}] Client receive error: {e}")
                        traceback.print_exc()
                        break

            # Outbound loop: Gemini -> FastAPI -> Client
            async def receive_from_gemini():
                try:
                    while True:
                        async for response in session.receive():
                          try:
                            # ── Handle tool_call at top level (Live API format) ──
                            tool_call = getattr(response, 'tool_call', None)
                            if tool_call is not None:
                                for fc in tool_call.function_calls:
                                    tool_name = fc.name
                                    tool_args = fc.args
                                    tool_id = getattr(fc, 'id', '')
                                    print(f"[{session_id}] 🔧 Tool call (Live API): {tool_name}({tool_args}) id={tool_id}")
                                    
                                    try:
                                        result_dict = await handle_tool_call(tool_name, tool_args)
                                    except Exception as e:
                                        print(f"[{session_id}] ✗ Tool execution error: {e}")
                                        traceback.print_exc()
                                        result_dict = {"error": str(e)}
                                    
                                    await session.send(
                                        input=types.LiveClientToolResponse(
                                            function_responses=[
                                                types.FunctionResponse(
                                                    name=tool_name,
                                                    id=tool_id,
                                                    response=result_dict
                                                )
                                            ]
                                        )
                                    )
                                    
                                    # Broadcast timer state
                                    state = await get_active_state()
                                    await websocket.send_text(json.dumps(state))
                                    
                                    # Broadcast pending UI commands
                                    pending = pop_pending_ui_commands()
                                    for cmd in pending:
                                        print(f"[{session_id}] 📤 Sending to frontend: {cmd.get('type')}")
                                        
                                        # Intercept timer complete to prompt Gemini
                                        if cmd.get("type") == "timer_complete":
                                            timer_name = cmd.get("timer_name", "Timer")
                                            print(f"[{session_id}] 🗣️ Prompting Gemini to announce timer: {timer_name}")
                                            await session.send(input=f"System Notification: The '{timer_name}' timer has just finished. Please briefly announce to the user that this timer is complete.", end_of_turn=True)

                                        await websocket.send_text(json.dumps(cmd))
                                continue

                            server_content = response.server_content
                            if server_content is not None:
                                # 1. Handle Audio output
                                if server_content.model_turn is not None:
                                    for part in server_content.model_turn.parts:
                                        if part.inline_data:
                                            try:
                                                if not hasattr(session, '_debug_audio_count'):
                                                    session._debug_audio_count = 0
                                                session._debug_audio_count += 1
                                                if session._debug_audio_count % 50 == 1:
                                                    print(f"[{session_id}] Gemini sent {len(part.inline_data.data)} bytes audio (x{session._debug_audio_count})")
                                                
                                                await websocket.send_bytes(part.inline_data.data)
                                            except Exception as e:
                                                print(f"[{session_id}] Error sending audio to client: {e}")
                                                return

                                # 2. Handle Tool Calls in server_content (fallback path)
                                if server_content.model_turn is not None:
                                    for part in server_content.model_turn.parts:
                                        if part.function_call:
                                            tool_name = part.function_call.name
                                            tool_args = part.function_call.args
                                            tool_id = getattr(part.function_call, 'id', '')
                                            print(f"[{session_id}] 🔧 Tool call (server_content): {tool_name}({tool_args}) id={tool_id}")
                                            
                                            try:
                                                result_dict = await handle_tool_call(tool_name, tool_args)
                                            except Exception as e:
                                                print(f"[{session_id}] ✗ Tool execution error: {e}")
                                                traceback.print_exc()
                                                result_dict = {"error": str(e)}
                                            
                                            await session.send(
                                                input=types.LiveClientToolResponse(
                                                    function_responses=[
                                                        types.FunctionResponse(
                                                            name=tool_name,
                                                            id=tool_id,
                                                            response=result_dict
                                                        )
                                                    ]
                                                )
                                            )
                                            
                                            # Broadcast state to frontend
                                            state = await get_active_state()
                                            await websocket.send_text(json.dumps(state))
                                            
                                            # Broadcast pending UI commands
                                            pending = pop_pending_ui_commands()
                                            for cmd in pending:
                                                print(f"[{session_id}] 📤 Sending to frontend: {cmd.get('type')}")
                                                await websocket.send_text(json.dumps(cmd))

                                # Log non-turn updates for debugging
                                if server_content.model_turn is None:
                                    interrupted = getattr(response.server_content, 'interrupted', False)
                                    if not interrupted:
                                        print(f"[{session_id}] Gemini turn_complete or non-turn update")

                            # Handle interruptions
                            if response.server_content and getattr(response.server_content, 'interrupted', False):
                                print(f"[{session_id}] Gemini interrupted response!")
                          except Exception as inner_e:
                            print(f"[{session_id}] ⚠ Error processing Gemini response (continuing): {inner_e}")
                            traceback.print_exc()
                        
                        # Wait a tiny bit between turns to avoid tight spinning if it disconnects
                        await asyncio.sleep(0.01)

                except asyncio.CancelledError:
                    print(f"[{session_id}] Gemini receive task was cancelled.")
                    return  # Only exit on cancellation (session stopped by user)
                except Exception as e:
                    print(f"[{session_id}] Gemini receive error (will retry in 1s): {e}")
                    traceback.print_exc()
                    await asyncio.sleep(1)  # Brief pause before retrying
                    # DON'T return — the while True loop will restart session.receive()

            # Background poller: checks for async events like timer completions
            async def poll_pending_commands():
                """
                Polls the pending_ui_commands queue every second.
                This catches timer completions and other async events that
                happen outside of Gemini tool call responses.
                """
                try:
                    while True:
                        await asyncio.sleep(1)
                        
                        # Also broadcast timer state periodically so the frontend
                        # countdown stays accurate
                        try:
                            state = await get_active_state()
                            if state.get("timers"):
                                await websocket.send_text(json.dumps(state))
                        except Exception:
                            pass

                        # Check for any queued commands (e.g. timer_complete)
                        pending_cmds = pop_pending_ui_commands()
                        for cmd in pending_cmds:
                            print(f"[{session_id}] 📤 [POLL] Sending to frontend: {cmd.get('type')}")
                            
                            # If a timer just completed, prompt Gemini to announce it
                            if cmd.get("type") == "timer_complete":
                                timer_name = cmd.get("timer_name", "Timer")
                                print(f"[{session_id}] 🗣️ [POLL] Prompting Gemini to announce timer: {timer_name}")
                                try:
                                    await session.send(
                                        input=f"System Notification: The '{timer_name}' timer has just finished. Please briefly announce to the user that this timer is complete.",
                                        end_of_turn=True
                                    )
                                except Exception as e:
                                    print(f"[{session_id}] Error prompting Gemini for timer: {e}")
                            
                            try:
                                await websocket.send_text(json.dumps(cmd))
                            except Exception as e:
                                print(f"[{session_id}] Error sending command to frontend: {e}")
                                return

                except asyncio.CancelledError:
                    print(f"[{session_id}] Poll task cancelled.")
                except Exception as e:
                    print(f"[{session_id}] Poll task error: {e}")

            # Run all three loops concurrently
            client_task = asyncio.create_task(receive_from_client())
            gemini_task = asyncio.create_task(receive_from_gemini())
            poll_task = asyncio.create_task(poll_pending_commands())

            done, pending = await asyncio.wait(
                [client_task, gemini_task, poll_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Identify which task finished first
            if client_task in done:
                print(f"[{session_id}] Client socket loop exited first.")
            if gemini_task in done:
                print(f"[{session_id}] Gemini SDK loop exited first.")
            if poll_task in done:
                print(f"[{session_id}] Poll task exited first.")
            
            for task in pending:
                task.cancel()

    except Exception as e:
        print(f"[{session_id}] Critical session error: {e}")
        traceback.print_exc()
        raise e
