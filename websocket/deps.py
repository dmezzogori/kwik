from typing import List

from broadcaster import Broadcast
from fastapi import WebSocket, Query
from fastapi import Depends
from fastapi import HTTPException, status

from app.kwik.api.deps import get_current_user
from app.kwik.db.session import DBContextManager

broadcast = Broadcast("postgres://postgres:root@db/app")


async def get_user(
    websocket: WebSocket,
    token: str = Query(None)
):
    try:
        with DBContextManager() as db:
            return get_current_user(db=db, token=token)
    except (HTTPException, AttributeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)

current_user = Depends(get_user)


class ConnectionManager:
    def __init__(self):
        self._websockets: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        self._websockets.append(websocket)
        await websocket.accept()

    async def broadcast(self, message: str):
        active_websockets = list(self._websockets)
        for websocket in self._websockets:
            try:
                await websocket.send_text(message)
            except:
                active_websockets.remove(websocket)

        self._websockets = active_websockets


manager = ConnectionManager()
