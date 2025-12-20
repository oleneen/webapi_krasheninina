import time
import logging
import asyncio
from typing import Optional, List

import httpx

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    Depends,
    BackgroundTasks,
    WebSocket,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    select,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.orm import sessionmaker

# ЛОГИРОВАНИЕ

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("req-logger")

# FASTAPI

app = FastAPI(
    title="TODO API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"{request.method} {request.url}")

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    logger.info(
        f"{request.method} {request.url} → {response.status_code} | {process_time:.4f}s"
    )

    return response

# DATABASE (ASYNC)

DATABASE_URL = "sqlite+aiosqlite:///./tasks.db"

Base = declarative_base()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# MODELS

class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    done = Column(Boolean, default=False)

# SCHEMAS

class TaskCreate(BaseModel):
    title: str
    description: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None

class Task(TaskCreate):
    id: int
    done: bool
    class Config:
        from_attributes = True

# WEBSOCKET MANAGER

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# BACKGROUND TASKS

async def generate_tasks(session: AsyncSession, count: int = 5):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://jsonplaceholder.typicode.com/todos"
        )
        data = response.json()[:count]

    for item in data:
        task = TaskModel(
            title=item["title"],
            description="generated",
            done=item["completed"]
        )
        session.add(task)

    await session.commit()

async def periodic_task_generator():
    while True:
        await asyncio.sleep(60)
        async with AsyncSessionLocal() as session:
            await generate_tasks(session, count=1)

# STARTUP

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    asyncio.create_task(periodic_task_generator())

# CRUD ENDPOINTS

@app.get("/tasks", response_model=List[Task])
async def get_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskModel))
    return result.scalars().all()

@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    new_task = TaskModel(**task.dict())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    await manager.broadcast({
        "event": "task_created",
        "task_id": new_task.id,
        "title": new_task.title,
    })

    return new_task


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    updated: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in updated.dict(exclude_unset=True).items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    await manager.broadcast({
        "event": "task_updated",
        "task_id": task.id,
    })

    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()

    await manager.broadcast({
        "event": "task_deleted",
        "task_id": task_id,
    })

# MANUAL BACKGROUND RUN

@app.post("/task-generator/run")
async def run_task_generator(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    background_tasks.add_task(generate_tasks, db)
    return {"status": "started"}

# WEBSOCKET

@app.websocket("/ws/tasks")
async def ws_tasks(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)
