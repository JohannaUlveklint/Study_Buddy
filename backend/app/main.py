from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.sessions import router as sessions_router
from app.api.routes.tasks import router as tasks_router


app = FastAPI(title="Study Buddy Phase 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(sessions_router)