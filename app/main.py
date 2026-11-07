import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers.api import router as api_router
from app.routers.views import views_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite database and tables are ready
    init_db()
    yield
    # Shutdown

app = FastAPI(
    title="Letterboxd JustWatch Italia",
    description="Trova i film della tua watchlist disponibili in streaming in Italia (abbonamenti o gratis)",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(views_router)
app.include_router(api_router)
