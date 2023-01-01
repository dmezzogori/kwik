import json

from fastapi import WebSocket

import kwik
from .deps import broadcast


async def send(
    websocket: WebSocket,
    data: dict | None = None,
    message: str | None = None,
):
    d = {"data": data or {}, "message": message or ""}
    t = json.dumps(d)
    kwik.logger.error(f"Sending: {t}")
    await websocket.send_text(t)
