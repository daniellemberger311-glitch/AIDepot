from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.api.router import router
from backend.log_handler import setup_logging
from backend.scheduler.jobs import start_scheduler, stop_scheduler, get_scheduler_info

# Logging so früh wie möglich initialisieren
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="AIDepot – Aktien- & Optionsschein-Analyse",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {
        "status":    "ok",
        "scheduler": get_scheduler_info(),
    }
