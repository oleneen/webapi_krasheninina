from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from pydantic import BaseModel
import asyncio

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, create_engine

Base = declarative_base()
engine = create_engine(
    "sqlite:///./tasks.db"
)
DBSession = sessionmaker(bind=engine, autoflush = False, autocommit = False)


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key = True, index = True)
    title = Column(String)
    description = Column(String)
    done = Column(Boolean, default = False)

Base.metadata.create_all(bind=engine)

async def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("req-logger")

app = FastAPI(title="TODO API", version="1.0")

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
    logger.info(f"📥 {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    logger.info(f"{request.method} {request.url} → {response.status_code} | {process_time:.4f}s")
    
    return response

class TaskCreate(BaseModel):
    title: str
    description: str 

class Task(TaskCreate):
    id: int
    done: bool = False

class TaskUpdate(BaseModel):
    title: str
    description: str
    done: bool

tasks: list[Task] = []
next_id = 1


@app.get("/tasks", response_model=list[Task])
async def get_tasks(db: DBSession = Depends(get_db)):
    return tasks

@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(task: TaskCreate):
    global next_id
    new_task = Task(id=next_id, title=task.title, description=task.description)
    tasks.append(new_task)
    next_id += 1
    return new_task

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    for t in tasks:
        if t.id == task_id:
            return t
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, updated: TaskUpdate):
    for idx, t in enumerate(tasks):
        if t.id == task_id:
            tasks[idx] = Task(
                id=t.id,
                title=updated.title,
                description=updated.description,
                done=updated.done
            )
            return tasks[idx]
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    for t in tasks:
        if t.id == task_id:
            tasks.remove(t)
            return
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/async_task()")
async def async_task():
    await asyncio.sleep(5)
    return {"message": "ok"}


from fastapi import BackgroundTasks

@app.get("/background_task")
async def background_task(background_task: BackgroundTasks):
    def slow_time():
        import time
        time.sleep(10)
        print("OK!!!!")
        print("OK!!!!")
        print("OK!!!!")
        print("OK!!!!")
        print("OK!!!!")

    background_task.add_task(slow_time)
    return {"message": "task started"}

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

io_executor = ThreadPoolExecutor(max_workers=2)

cpu_executor = ProcessPoolExecutor(max_workers=2)

def blocking_io_task():
    import time
    time.sleep(6)
    return "ok"

@app.get("/thread_pool_sleep")
async def thread_pool_sleep():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(io_executor, blocking_io_task)
    return {"message": result}

def heavy_func(n: int):
    result = 0
    for i in range(n):
        result += i * i
    "foo" * n
    return result

@app.get("/cpu_task")
async def cpu_task(n: int = 10_000_000):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(cpu_executor, heavy_func, n)
    return {"message": result}
