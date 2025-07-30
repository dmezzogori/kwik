"""WebSocket utilities package for kwik framework.

This package provides WebSocket functionality and utilities for real-time
communication within the kwik web framework.
"""

from fastapi import WebSocket


async def send(
    websocket: WebSocket,
    data: dict | None = None,
    message: str | None = None,
) -> None:
    """Send data or text message through WebSocket connection."""
    if data is not None and message is not None:
        msg = "Only one of data or message should be provided"
        raise ValueError(msg)

    if message is not None:
        await websocket.send_text(message)
    elif data is not None:
        await websocket.send_json(data)
    else:
        msg = "Either data or message should be provided"
        raise ValueError(msg)


__all__ = [
    "send",
]
