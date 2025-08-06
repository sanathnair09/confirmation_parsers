from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connection: WebSocket | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connection = websocket

    def disconnect(self):
        self._connection = None

    async def send_file_ready(self, filename: str):
        if self._connection:
            await self._connection.send_json(
                {"event": "file_ready", "filename": filename}
            )

    async def send_job_update(self, job_id: str, status: dict[str, Any]):
        if self._connection:
            await self._connection.send_json(
                {"event": "job_update", "job_id": job_id, "status": status}
            )
