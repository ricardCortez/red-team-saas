"""WebSocket event definitions and handlers"""
import json
import logging
from typing import Optional
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


class EventType:
    SCAN_PROGRESS = "scan_progress"
    SCAN_COMPLETED = "scan_completed"
    FINDING_NEW = "finding_new"
    ALERT = "alert"
    NOTIFICATION = "notification"
    SUBSCRIBE_SCAN = "subscribe_scan"
    UNSUBSCRIBE_SCAN = "unsubscribe_scan"
    PING = "ping"
    PONG = "pong"


async def handle_client_message(user_id: int, raw: str) -> Optional[dict]:
    """Handle incoming message from WebSocket client.

    Returns a response dict if the message warrants one, else None.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "error", "payload": {"message": "Invalid JSON"}}

    msg_type = data.get("type")

    if msg_type == EventType.PING:
        return {"type": EventType.PONG, "payload": {}}

    if msg_type == EventType.SUBSCRIBE_SCAN:
        scan_id = data.get("payload", {}).get("scan_id")
        if scan_id is not None:
            await ws_manager.subscribe_scan(user_id, int(scan_id))
            logger.info(f"User {user_id} subscribed to scan {scan_id}")
            return {"type": "subscribed", "payload": {"scan_id": scan_id}}

    if msg_type == EventType.UNSUBSCRIBE_SCAN:
        scan_id = data.get("payload", {}).get("scan_id")
        if scan_id is not None:
            await ws_manager.unsubscribe_scan(user_id, int(scan_id))
            return {"type": "unsubscribed", "payload": {"scan_id": scan_id}}

    return None


# Helper functions for use in Celery tasks or services
async def emit_scan_progress(scan_id: int, progress: int, status: str, details: str = "") -> None:
    await ws_manager.send_scan_progress(scan_id, progress, status, details)


async def emit_scan_completed(scan_id: int, findings_count: int) -> None:
    await ws_manager.send_scan_completed(scan_id, findings_count)


async def emit_new_finding(user_id: int, finding: dict) -> None:
    await ws_manager.send_new_finding(user_id, finding)


async def emit_alert(user_id: int, title: str, message: str, severity: str = "info") -> None:
    await ws_manager.send_alert(user_id, title, message, severity)


async def emit_notification(user_id: int, title: str, message: str, severity: str = "info") -> None:
    await ws_manager.send_notification(user_id, title, message, severity)
