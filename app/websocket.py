from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from dotenv import load_dotenv
import json
from app.models.database import SessionLocal, PhishingTarget

router = APIRouter()
load_dotenv()


# -------------------------
# Connection Manager
# -------------------------
class ConnectionManager:
    def __init__(self, isUserID: bool = False):
        self.isUserID = isUserID
        if self.isUserID:
            self.active_connections: dict[int, list[WebSocket]] = {}
        else:
            self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, user_id: int = None):
        await websocket.accept()
        if self.isUserID:
            if user_id is None:
                raise ValueError("user_id is required for per-user connections")
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
            print(f"🔗 User {user_id} connected. Total: {len(self.active_connections[user_id])}")
        else:
            self.active_connections.append(websocket)
            print(f"🔗 Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: int = None):
        if self.isUserID:
            if user_id in self.active_connections and websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        else:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: str, sender: WebSocket = None, user_id: int = None):
        to_remove = []

        if self.isUserID:
            if user_id not in self.active_connections:
                return
            for conn in self.active_connections[user_id]:
                try:
                    await conn.send_text(message)
                except Exception as e:
                    print(f"⚠️ Failed to send to user {user_id}: {e}")
                    to_remove.append(conn)
            for conn in to_remove:
                self.disconnect(conn, user_id)
        else:
            for conn in self.active_connections:
                if conn != sender:
                    try:
                        await conn.send_text(message)
                    except Exception as e:
                        print(f"⚠️ Failed to send to client: {e}")
                        to_remove.append(conn)
            for conn in to_remove:
                self.disconnect(conn)

    async def broadcast_all(self, message: str):
        """Broadcast to ALL connected clients including sender."""
        to_remove = []
        for conn in self.active_connections:
            try:
                await conn.send_text(message)
            except Exception as e:
                print(f"⚠️ Failed to broadcast: {e}")
                to_remove.append(conn)
        for conn in to_remove:
            self.disconnect(conn)


# -------------------------
# Manager instances
# -------------------------
dashboard_manager = ConnectionManager()


# -------------------------
# Helper: push a tracking event to all dashboard clients
# -------------------------
async def push_tracking_event(event_type: str, email: str, extra: dict = None):
    """
    Call this from your tracking endpoints (open/click) to push
    a real-time update to every connected dashboard.

    event_type: "opened" | "clicked" | "stats_update"
    email:      the recipient's email address
    extra:      any additional payload fields
    """
    payload = {
        "type": event_type,
        "email": email,
        **(extra or {}),
    }
    await dashboard_manager.broadcast_all(json.dumps(payload))
    print(f"📡 Pushed {event_type} event for {email}")


def _build_stats_update_payload() -> str:
    db = SessionLocal()
    try:
        targets = db.query(PhishingTarget).all()
        table_data = [
            {
                "email": t.email,
                "sent": t.is_sent,
                "opened": t.is_opened,
                "clicked": t.is_clicked,
                "compromised": t.is_compromised
            }
            for t in targets
        ]
        return json.dumps({"type": "stats_update", "data": table_data})
    finally:
        db.close()


async def broadcast_stats_snapshot():
    await dashboard_manager.broadcast_all(_build_stats_update_payload())


# -------------------------
# WebSocket Route
# -------------------------
@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await dashboard_manager.connect(websocket)
    await websocket.send_text(_build_stats_update_payload())
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                print(f"⚠️ Invalid dashboard message: {data}")
                continue

            if message.get("action") == "sync_stats":
                await websocket.send_text(_build_stats_update_payload())
    except WebSocketDisconnect:
        dashboard_manager.disconnect(websocket)
        print("🔌 Dashboard client disconnected")


__all__ = ["router", "dashboard_manager", "push_tracking_event", "broadcast_stats_snapshot"]