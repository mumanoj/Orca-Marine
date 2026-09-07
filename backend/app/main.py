import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.health import router as health_router
from app.routes.query import router as query_router
from app.routes.websocket import router as ws_router
from app.routes.map import router as map_router
from app.db import init_db, close_db, is_db_connected

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ORCA Platform (Phase 1-5 Foundation).")
    # Initialize Beanie MongoDB connection asynchronously
    db_success = await init_db()
    if db_success:
        logger.info("MongoDB persistence active.")
    else:
        logger.warning("MongoDB unavailable. Operating in graceful in-memory fallback mode.")
    yield
    close_db()
    logger.info("Shutting down ORCA Platform.")

# Initialize FastAPI App
app = FastAPI(
    title="ORCA — Agentic AI Marine Intelligence Platform",
    description="Conversational Geospatial Decision Support for Marine Stakeholders",
    version="1.0.0-phase5",
    lifespan=lifespan
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(ws_router, prefix="/api")
app.include_router(map_router, prefix="/api")
