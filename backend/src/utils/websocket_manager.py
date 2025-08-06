# websocket_manager.py

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connection: WebSocket | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connection = websocket

    def disconnect(self):
        self._connection = None

    async def send_file_ready(self, download_url: str):
        if self._connection:
            await self._connection.send_json(
                {"event": "file_ready", "download_url": download_url}
            )
