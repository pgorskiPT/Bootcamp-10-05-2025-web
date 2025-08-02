from fastapi import FastAPI, BackgroundTasks, status
from async_db import init_db, add_task, get_tasks
from pydantic import BaseModel
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


class Task(BaseModel):
    title: str


# http://127.0.0.1:8000/tasks/
# pobranie listy zadan z bazy i zwrócenie jako json
@app.get("/tasks/")
async def read_tasks():
    tasks = await get_tasks()
    return {"tasks": [{"id": t[0], "title": t[1]} for t in tasks]}


@app.post("/tasks/", status_code=status.HTTP_201_CREATED)
async def create_task(task: Task, background_tasks: BackgroundTasks):
    background_tasks.add_task(add_task, task.title)
    return {"message": "Task creation scheduled"}
