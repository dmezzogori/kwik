from fastapi import WebSocket


async def send(
    websocket: WebSocket,
    data: dict | None = None,
    message: str | None = None,
):
    if data is not None and message is not None:
        raise ValueError("Only one of data or message should be provided")

    if message is not None:
        await websocket.send_text(message)
    elif data is not None:
        await websocket.send_json(data)
    else:
        raise ValueError("Either data or message should be provided")
