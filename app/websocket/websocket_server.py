from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json
from datetime import datetime,timezone
from app.services import (
    create_message,
    update_message_status,
    mark_message_seen,
    get_or_create_conversation,
    set_user_online,
    set_user_offline,
    get_undelivered_messages,
)
from app.db import get_app_db_connection


active_connections: Dict[str, WebSocket] = {}
online_users = set()

def websocket_app(app):
    @app.websocket("/ws/{user_id}")
    async def chat_socket(websocket: WebSocket, user_id: str):
        await websocket.accept()
        active_connections[user_id] = websocket
        online_users.add(user_id)
        set_user_online(user_id)
        for uid, ws in active_connections.items():
            if uid != user_id:
                await ws.send_json({
                    "type": "user_status",
                    "user_id": user_id,
                    "is_online": True
                })
        print(f"🔌 {user_id} connected")

        # Send undelivered messages
        try:
            missed = get_undelivered_messages(user_id)
            for msg in missed:
                try:
                    await websocket.send_json({
                        "id": str(msg["message_id"]),
                        "sender_id": msg["sender_id"],
                        "receiver_id": msg["receiver_id"],
                        "body": msg.get("content") or msg.get("message") or "",
                        "replied_to": msg.get("reply_to_message_id"),
                        "time": msg.get("sent_at").strftime("%I:%M %p") if msg.get("sent_at") else None,
                        "day": msg.get("sent_at").isoweekday() if msg.get("sent_at") else None,
                        "b_deleted": msg.get("b_deleted", False),
                        "status": msg.get("status", 1),
                        "image_name": msg.get("image_name"),
                        "local_image_name": msg.get("local_image_name")
                    })
                    update_message_status(msg["message_id"], "delivered")
                except Exception as e:
                    print("Error sending missed message:", e)
        except Exception as e:
            print(f"🔥 Failed to send undelivered messages: {e}")

        try:
            while True:     
                try:
                    raw_data = await websocket.receive_text()
                    data = json.loads(raw_data)
                    print(f"✅ Received from {user_id}:", data)
                except WebSocketDisconnect:
                    print(f"❌ {user_id} disconnected inside loop")
                    # Properly handle WebSocket disconnect
                    active_connections.pop(user_id, None)  # Remove from active connections
                    online_users.discard(user_id)
                    set_user_offline(user_id)
                    break  # Exit loop after disconnection
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON from {user_id}: {raw_data}")
                    continue
                except Exception as e:
                    print(f"🔥 Unexpected receive error: {e}")
                    break

                event_type = data.get("type")

                try:
                    if event_type in ["message", "file"]:
                        await handle_message(data, user_id)

                    elif event_type == "seen":
                        message_id = data.get("message_id")
                        mark_message_seen(message_id)
                        # Notify sender that their message was seen
                        from_user = data.get("from")
                        conn = get_app_db_connection()
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("SELECT sender_id FROM messages WHERE message_id = %s", (message_id,))
                        row = cursor.fetchone()
                        if row:
                            sender_id = str(row["sender_id"])
                            if sender_id in active_connections:
                                await active_connections[sender_id].send_json({
                                    "type": "status_update",
                                    "message_id": message_id,
                                    "status": "seen"
                                })
                        cursor.close()
                        conn.close()

                        sender_id = data.get("from")
                        if sender_id in active_connections:
                            await active_connections[sender_id].send_json({
                                "type": "status_update",
                                "message_id": message_id,
                                "status": "seen"
                            })

                    elif event_type == "typing":
                        receiver_id = str(data.get("to"))
                        is_typing = data.get("is_typing", False)
                        if receiver_id in active_connections:
                            await active_connections[receiver_id].send_json({
                                "type": "typing",
                                "from": user_id,
                                "is_typing": is_typing
                            })
                    else:
                        print(f"⚠️ Unknown event type from {user_id}: {event_type}")
                except Exception as e:
                    print(f"🔥 Error handling {event_type} from {user_id}: {e}")

        except WebSocketDisconnect:
            print(f"❌ {user_id} disconnected")
        except Exception as e:
            print(f"🔥 Top-level WebSocket error for {user_id}: {e}")
        finally:
            active_connections.pop(user_id, None)
            online_users.discard(user_id)
            set_user_offline(user_id)
            for uid, ws in active_connections.items():
                if uid != user_id:
                    await ws.send_json({
                        "type": "user_status",
                        "user_id": user_id,
                        "is_online": False
                    })


async def handle_message(data, sender_id):
    try:
        sender_id = str(sender_id)
        receiver_id = str(data.get("to"))
        msg_type = data.get("type", "message")
        content = data.get("message", "").strip()
        reply_to_message_id = data.get("reply_to_message_id")

        file_url = data.get("file_url") if msg_type == "file" else None
        file_type = data.get("file_type") if msg_type == "file" else None

        # 1. Validate message content
        if msg_type == "message" and not content:
            await active_connections[sender_id].send_json({
                "type": "error",
                "message": "Message content cannot be empty."
            })
            return

        # 2. Validate file message requirements
        if msg_type == "file" and (not file_url or not file_type):
            await active_connections[sender_id].send_json({
                "type": "error",
                "message": "Missing file_url or file_type for file message."
            })
            return

        # 3. Get or create conversation ID
        conversation_id = await get_or_create_conversation(sender_id, receiver_id)
        if not conversation_id:
            await active_connections[sender_id].send_json({
                "type": "error",
                "message": "Failed to get or create conversation."
            })
            return

        # 4. Create message
        message_payload = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "status": 1,
            "message_type": msg_type,
            "content": content,
            "file_url": file_url,
            "file_type": file_type,
            "reply_to_message_id": reply_to_message_id
        }

        msg_result = create_message(message_payload)
        msg_id = msg_result["message_id"]
        now = datetime.now()
        message_data = {
            "id": str(msg_id),
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "body": content,
            "replied_to": reply_to_message_id,
            "time": now.strftime("%I:%M %p"),
            "day": now.isoweekday(),
            "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "b_deleted": False,
            "status": 1,
            "image_name": "image_001.jpg" if msg_type == "file" else None,
            "local_image_name": "image_local_001.jpg" if msg_type == "file" else None
        }

        # 5. Send message to receiver only
        if receiver_id in active_connections:
            await active_connections[receiver_id].send_json(message_data)
            update_message_status(msg_id, "delivered")

        # 6. Confirm to sender
        if sender_id in active_connections:
            await active_connections[sender_id].send_json({
                "type": "status_update",
                "message_id": msg_id,
                "status": "delivered" if receiver_id in active_connections else "sent"
            })

    except Exception as e:
        print(f"🔥 Error handling message from {sender_id}: {e}")
        if sender_id in active_connections:
            await active_connections[sender_id].send_json({
                "type": "error",
                "message": f"Error processing message: {e}"
            })
