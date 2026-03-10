"""
main.py
App setup and middleware only. Nothing else lives here.

To run:
  uvicorn main:app --reload --port 8000
"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from endpoints.session import router as session_router
from endpoints.websocket import router as websocket_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kitchen_copilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Kitchen Copilot starting...")
    yield
    logger.info("Kitchen Copilot shutting down...")


app = FastAPI(
    title="Kitchen Copilot API",
    version="1.0.0",
    lifespan=lifespan
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React dev server
        "http://localhost:5173",   # Vite dev server
        "http://localhost:5174",   # Vite alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(session_router)
app.include_router(websocket_router)