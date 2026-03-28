"""WebSocket endpoints for real-time updates"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import JWTHandler
from app.websocket.manager import ws_manager
from app.websocket.events import handle_client_message

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    """Main WebSocket endpoint.

    Clients connect with ?token=<jwt_access_token>.
    Once authenticated, they receive real-time events and can
    subscribe to scan progress updates.
    """
    # Authenticate
    payload = JWTHandler.verify_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = int(payload.get("sub", 0))
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    await ws_manager.connect(websocket, user_id)

    try:
        # Send welcome
        await ws_manager.send_personal(user_id, {
            "type": "connected",
            "payload": {
                "user_id": user_id,
                "message": "Connected to Red Team SaaS real-time updates",
            },
        })

        # Message loop
        while True:
            raw = await websocket.receive_text()
            response = await handle_client_message(user_id, raw)
            if response:
                await ws_manager.send_personal(user_id, response)

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)
    except Exception as exc:
        logger.error(f"WebSocket error for user {user_id}: {exc}")
        await ws_manager.disconnect(websocket, user_id)


@router.websocket("/ws/scan/{scan_id}")
async def websocket_scan_endpoint(
    websocket: WebSocket,
    scan_id: int,
    token: str = Query(default=""),
):
    """WebSocket endpoint for a specific scan's real-time progress.

    Auto-subscribes the user to the given scan_id events.
    """
    payload = JWTHandler.verify_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = int(payload.get("sub", 0))
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    await ws_manager.connect(websocket, user_id)
    await ws_manager.subscribe_scan(user_id, scan_id)

    try:
        await ws_manager.send_personal(user_id, {
            "type": "subscribed",
            "payload": {"scan_id": scan_id},
        })

        while True:
            raw = await websocket.receive_text()
            response = await handle_client_message(user_id, raw)
            if response:
                await ws_manager.send_personal(user_id, response)

    except WebSocketDisconnect:
        await ws_manager.unsubscribe_scan(user_id, scan_id)
        await ws_manager.disconnect(websocket, user_id)
    except Exception as exc:
        logger.error(f"WebSocket scan error user={user_id} scan={scan_id}: {exc}")
        await ws_manager.unsubscribe_scan(user_id, scan_id)
        await ws_manager.disconnect(websocket, user_id)
