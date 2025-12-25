import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .db.base import engine, Base
from .nats_client.client import close_nats_client
from .nats_client.handlers import subscribe_to_nats
from .tasks.background import periodic_fetch_task
from .api.routes import router as api_router
from .ws.manager import manager
import logging
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await subscribe_to_nats()

    asyncio.create_task(periodic_fetch_task())

    yield

    await close_nats_client()

app = FastAPI(
    title="Currency Rates API",
    version="1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

@app.websocket("/ws/rates")
async def ws_rates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)