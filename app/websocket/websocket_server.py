from fastapi import WebSocket, WebSocketDisconnect
import logging
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

# User typing notification
async def handle_typing(data, sender_id):
    receiver_id = str(data.get("to"))
    is_typing = data.get("is_typing", False)

    if receiver_id in active_connections:
        await active_connections[receiver_id].send_json({
            "type": "typing",
            "from": sender_id,
            "is_typing": is_typing
        })

# Sending undelivered messages
async def send_undelivered_messages(user_id, websocket):
    undelivered_messages = get_undelivered_messages(user_id)
    for message in undelivered_messages:
        await websocket.send_json({
            "id": str(message["message_id"]),
            "sender_id": message["sender_id"],
            "receiver_id": message["receiver_id"],
            "body": message.get("body"),
            "status": "sent"
        })
        update_message_status(message["message_id"], "delivered")

# Notify user status to all connected users
async def send_user_status_update(user_id, is_online):
    for uid, ws in active_connections.items():
        if uid != user_id:
            await ws.send_json({
                "type": "user_status",
                "user_id": user_id,
                "is_online": is_online
            })

async def handle_delete(data, sender_id):
    message_id = data.get("message_id")
    delete_message(message_id)

    # Notify all connected users about the message deletion
    for user_id, ws in active_connections.items():
        await ws.send_json({
            "type": "message_deleted",
            "message_id": message_id
        })
    # Delete message function
def delete_message(message_id):
    conn = get_app_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Messages SET b_deleted = 1 WHERE id = %s", (message_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # Mark message as seen
def mark_message_seen(message_id):
    update_message_status(message_id, "seen")



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
                    "body": msg.get("content") or msg.get("message") or "",  # Use 'body' if 'content' is not available
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



logging.basicConfig(level=logging.DEBUG)

async def handle_message(data, sender_id):
    try:
        sender_id = str(sender_id)
        receiver_id = str(data.get("to"))
        msg_type = data.get("type", "message")
        message_content = data.get("message", "").strip()

        if not message_content:
            message_content = "No content"

        # Get or create conversation
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            conversation_id = await get_or_create_conversation(sender_id, receiver_id)

        # Prepare payload
        message_payload = {
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "status": 1,
            "message_type": msg_type,
            "content": message_content,
            "file_url": data.get("file_url"),
            "file_type": data.get("file_type"),
            "reply_to_message_id": data.get("reply_to_message_id")
        }

        msg_result = create_message(message_payload)
        msg_id = msg_result.get("message_id")
        if not msg_id:
            raise ValueError("Message ID could not be created")

        # ✅ Notify sender
        if sender_id in active_connections:
            await active_connections[sender_id].send_json({
                "type": "message",
                "message_id": msg_id,
                "status": "sent",
                "content": message_content
            })

        # ✅ Notify receiver (🔥 this was missing)
        if receiver_id in active_connections:
            sent_at = datetime.utcnow()  # or fetch from DB if needed
            await active_connections[receiver_id].send_json({
                "type": "message",
                "id": str(msg_id),
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "body": message_content,
                "replied_to": data.get("reply_to_message_id"),
                "time": sent_at.strftime("%I:%M %p"),
                "day": sent_at.weekday(),
                "b_deleted": False,
                "status": 1,
                "image_name": data.get("image_name"),
                "local_image_name": data.get("local_image_name"),
                "date": sent_at.isoformat()
            })

    except Exception as e:
        logging.error(f"🔥 Error processing message: {e}")
        if sender_id in active_connections:
            await active_connections[sender_id].send_json({
                "type": "error",
                "message": f"Error processing message: {str(e)}"
            })



