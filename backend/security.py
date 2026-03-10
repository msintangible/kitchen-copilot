"""
security.py
Token generation and validation for WebSocket connections.

WHY TOKENS FOR WEBSOCKETS:
WebSockets can't send Authorization headers like HTTP requests.
So we use a short-lived token in the URL query param instead:
  ws://localhost:8000/ws?token=abc123

Flow:
  1. Frontend calls POST /session/token (HTTP)
  2. Backend generates token, stores it, returns it
  3. Frontend opens WebSocket with ?token=abc123
  4. Backend validates token, deletes it (one-time use)
"""

import secrets
import logging

logger = logging.getLogger("kitchen_copilot.security")

# In-memory token store: token → session_id
# In production swap this for Redis with a TTL
active_tokens: dict[str, str] = {}


def generate_session_token() -> tuple[str, str]:
    """
    Creates a new session token and session ID.
    Returns (token, session_id).
    """
    token = secrets.token_urlsafe(32)
    session_id = f"sess_{secrets.token_hex(8)}"
    active_tokens[token] = session_id
    logger.info(f"Token created for session: {session_id}")
    return token, session_id


def validate_and_consume_token(token: str) -> str | None:
    """
    Validates a token and returns the session_id if valid.
    Deletes the token after use — one time only.
    Returns None if token is invalid.
    """
    session_id = active_tokens.pop(token, None)
    if session_id:
        logger.info(f"Token consumed for session: {session_id}")
    else:
        logger.warning(f"Invalid token attempted: {token[:8]}...")
    return session_id