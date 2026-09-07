import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global MongoDB connection state tracer
_is_db_connected: bool = False
_db_client: Optional[Any] = None # type: ignore

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    HAS_MOTOR_BEANIE = True
except ImportError:
    HAS_MOTOR_BEANIE = False
    logger.info("Motor / Beanie packages not installed. Operating in Memory-Fallback Mode.")

async def init_db() -> bool:
    """
    Initializes Motor AsyncIOMotorClient and Beanie document models if installed.
    Non-blocking: If MongoDB is unavailable or packages are missing, logs a warning
    and sets _is_db_connected = False so the system operates cleanly in-memory.
    """
    global _is_db_connected, _db_client
    if not HAS_MOTOR_BEANIE:
        _is_db_connected = False
        return False

    from app.core.config import settings
    from app.db_models import ConversationDocument, MessageDocument, ExecutionTraceDocument

    try:
        logger.info(f"Attempting MongoDB connection to {settings.MONGODB_URL} (Database: {settings.MONGODB_DATABASE})...")
        _db_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=10000  # 10 second timeout for Atlas SSL/TLS connection check
        )
        
        # Ping the server to verify connectivity
        await _db_client.admin.command('ping')
        
        # Initialize Beanie documents
        await init_beanie(
            database=_db_client[settings.MONGODB_DATABASE],
            document_models=[
                ConversationDocument,
                MessageDocument,
                ExecutionTraceDocument
            ]
        )
        _is_db_connected = True
        logger.info("MongoDB & Beanie initialized successfully!")
        return True

    except Exception as e:
        _is_db_connected = False
        logger.warning(f"MongoDB connection unavailable ({e}). ORCA operating in Memory-Fallback Mode.")
        return False

def is_db_connected() -> bool:
    """Returns True if MongoDB Beanie connection is active."""
    return _is_db_connected

def close_db():
    """Closes MongoDB connection client if open."""
    global _db_client, _is_db_connected
    if _db_client and hasattr(_db_client, "close"):
        _db_client.close()
        _is_db_connected = False
        logger.info("MongoDB client closed.")
