"""
routes/websocket.py
WebSocket endpoint — accepts the connection and kicks off the session.
Delegates all real work to services/gemini.py and services/audio.py.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from Backend.security import validate_and_consume_token
from Backend.services.gemini_live import run_gemini_session

logger = logging.getLogger("kitchen_copilot.routes.websocket")
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="One-time session token from POST /session/token")
):
    """
    Main WebSocket endpoint.

    Frontend connects with:
      new WebSocket("ws://localhost:8000/ws?token=abc123")

    What happens here:
      1. Validate the token
      2. Accept the WebSocket
      3. Hand off to run_gemini_session() in services/gemini.py
    """

    # Validate token before accepting the connection
    session_id = validate_and_consume_token(token)
    if not session_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Accept the connection
    await websocket.accept()
    logger.info(f"WebSocket accepted: {session_id}")

    # Tell the frontend the session is ready
    await websocket.send_text(json.dumps({
        "type": "session_ready",
        "session_id": session_id
    }))

    try:
        # Hand off to gemini service — this runs for the full session duration
        await run_gemini_session(websocket, session_id)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")

    except Exception as e:
        logger.error(f"Session error [{session_id}]: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except Exception:
            pass

    finally:
        logger.info(f"Session closed: {session_id}")