import json
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    """
    Manages active WebSocket connections mapped by client ID.
    Enables streaming execution trace state events dynamically.
    """
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_event(self, client_id: str, event_type: str, data: dict):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            payload = {
                "event_type": event_type,
                "data": data
            }
            try:
                await websocket.send_text(json.dumps(payload))
            except Exception as e:
                logger.error(f"Failed to send WS event to {client_id}: {e}")
                self.disconnect(client_id)

manager = ConnectionManager()

@router.websocket("/ws/trace/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        # Keep connection open and listen for incoming messages if any
        while True:
            # We don't expect messages from client for now, but need to check for disconnection
            data = await websocket.receive_text()
            # Echo or process if needed
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)

async def stream_trace_event(client_id: str, event_type: str, data: dict):
    """
    Exported helper function to push trace telemetry to active connections.
    """
    await manager.send_event(client_id, event_type, data)
