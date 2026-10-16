import json
from fastapi import WebSocket, WebSocketDisconnect


class WebSocketConnectionManager:
    def __init__(self):
        # { user_id: WebSocket }
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str, websocket: WebSocket | None = None):
        current = self.active_connections.get(user_id)
        if websocket is None or current is websocket:
            self.active_connections.pop(user_id, None)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections

    async def send_to_user(self, user_id: str, payload: dict) -> bool:
        """Send a message to a specific user if they are online."""
        ws = self.active_connections.get(str(user_id))
        if ws is None:
            return False
        try:
            await ws.send_text(json.dumps(payload))
            return True
        except (WebSocketDisconnect, RuntimeError):
            self.disconnect(str(user_id), ws)
            return False

    async def force_disconnect(self, user_id: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.close()
            self.disconnect(user_id, ws)


manager = WebSocketConnectionManager()
