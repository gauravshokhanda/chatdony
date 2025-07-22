from app.db import get_app_db_connection
from datetime import datetime

# 🔁 Status mapping (reuse across functions)
STATUS_MAP = {
    "sent": 1,
    "delivered": 2,
    "seen": 3
}

# Create or get a private conversation
async def get_or_create_conversation(uuid1, uuid2):
    conn = get_app_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT cp1.conversation_id
        FROM conversation_participants cp1
        JOIN conversation_participants cp2 ON cp1.conversation_id = cp2.conversation_id
        WHERE cp1.user_id = %s AND cp2.user_id = %s
        LIMIT 1
    """
    cursor.execute(query, (uuid1, uuid2))
    result = cursor.fetchone()

    if result:
        cursor.close()
        conn.close()
        return result[0]

    cursor.execute("INSERT INTO conversations (room_name) VALUES (%s)", (f"chat_{uuid1}_{uuid2}",))
    conversation_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO conversation_participants (conversation_id, user_id)
        VALUES (%s, %s), (%s, %s)
    """, (conversation_id, uuid1, conversation_id, uuid2))

    conn.commit()
    cursor.close()
    conn.close()

    return conversation_id


# Create new message
def create_message(data):
    conn = get_app_db_connection()
    cursor = conn.cursor()

    status = data.get("status", 1)
    if isinstance(status, str):
        status = STATUS_MAP.get(status.lower(), 1)

    sql = """
    INSERT INTO Messages (
        conversation_id, sender_id, receiver_id,
        body, replied_to, image_name, local_image_name,
        b_deleted, status, message_type, file_url, file_type,
        sent_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """

    values = (
        data["conversation_id"],
        data["sender_id"],
        data["receiver_id"],
        data.get("body", ""),  # ✅ Changed from 'message' to 'body'
        data.get("replied_to"),
        data.get("image_name"),
        data.get("local_image_name"),
        data.get("b_deleted", 0),
        status,
        data.get("message_type", "message"),
        data.get("file_url"),
        data.get("file_type")
    )

    cursor.execute(sql, values)
    conn.commit()
    message_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return {"message_id": message_id}


# Update message status
def update_message_status(message_id, status):
    if isinstance(status, str):
        status = STATUS_MAP.get(status.lower(), 1)

    conn = get_app_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Messages SET status = %s WHERE id = %s", (status, message_id))
    conn.commit()
    cursor.close()
    conn.close()


# Mark message as seen
def mark_message_seen(message_id):
    conn = get_app_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Messages SET status = %s WHERE id = %s", (STATUS_MAP["seen"], message_id))
    conn.commit()
    cursor.close()
    conn.close()


# Set user online
def set_user_online(uuid):
    conn = get_app_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE UserTable SET isActive = 1 WHERE uniqueUDID = %s", (uuid,))
    conn.commit()
    cursor.close()
    conn.close()


# Set user offline with timestamp
def set_user_offline(uuid):
    conn = get_app_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE UserTable SET isActive = 0, lastActiveTime = %s WHERE uniqueUDID = %s",
        (datetime.now(), uuid)
    )
    conn.commit()
    cursor.close()
    conn.close()


# Get user status
def get_user_status(uuid):
    conn = get_app_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT isActive, lastActiveTime FROM UserTable WHERE uniqueUDID = %s", (uuid,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


# Fetch undelivered messages
def get_undelivered_messages(uuid):
    conn = get_app_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM Messages
        WHERE receiver_id = %s AND status = %s
        ORDER BY sent_at ASC
    """, (uuid, STATUS_MAP["sent"]))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


# Get user name
def get_user_name(uuid):
    conn = get_app_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM UserTable WHERE uniqueUDID = %s", (uuid,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else "User"
