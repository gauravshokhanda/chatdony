from fastapi import APIRouter, HTTPException, Query
from app.db import get_app_db_connection, get_openfire_db_connection
from datetime import datetime

router = APIRouter()

def format_null(value):
    return value if value not in [None, ""] else "<null>"

@router.get("/conversation/byuuid/{uuid}")
def get_chat_partners(uuid: str, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    conn = get_app_db_connection()  # telehotwire DB
    cursor = conn.cursor(dictionary=True)

    offset = (page - 1) * limit

    # Fetch distinct chat partner UUIDs from Messages table
    query = """
        SELECT sender_id, receiver_id
        FROM Messages
        WHERE sender_id = %s OR receiver_id = %s
    """
    cursor.execute(query, (uuid, uuid))
    rows = cursor.fetchall()

    partner_uuids: Set[str] = set()
    for row in rows:
        if row["sender_id"] != uuid:
            partner_uuids.add(row["sender_id"])
        elif row["receiver_id"] != uuid:
            partner_uuids.add(row["receiver_id"])

    # Paginate manually after set
    partner_uuids = list(partner_uuids)
    total = len(partner_uuids)
    paginated_uuids = partner_uuids[offset:offset + limit]

    user_map = {}
    if paginated_uuids:
        placeholders = ",".join(["%s"] * len(paginated_uuids))
        cursor.execute(
            f"""SELECT uniqueUDID, name, email, profilePic, gender, phoneNumber,
                       lastActiveTime, description, isActive
                FROM UserTable
                WHERE uniqueUDID IN ({placeholders})""",
            paginated_uuids
        )
        users = cursor.fetchall()
        user_map = {u["uniqueUDID"]: u for u in users}

    partners = []
    for uid in paginated_uuids:
        user = user_map.get(uid)
        if user:
            partners.append({
                "uniqueUDID": format_null(user.get("uniqueUDID")),
                "name": format_null(user.get("name")),
                "email": format_null(user.get("email")),
                "profilePic": format_null(user.get("profilePic")),
                "gender": format_null(user.get("gender")),
                "phoneNumber": format_null(user.get("phoneNumber")),
                "lastActiveTime": format_null(user.get("lastActiveTime")),
                "matchId": 0,
                "description": format_null(user.get("description")),
            })

    cursor.close()
    conn.close()

    return {
        "code": 200,
        "success": True,
        "page": page,
        "limit": limit,
        "data": {
            "count": len(partners),
            "results": partners
        }
    }


# Get chat history between two UUIDs (Paginated)
@router.get("/conversation/{uuid1}/{uuid2}", tags=["Chat"])
def get_conversation_by_uuid(
    uuid1: str,
    uuid2: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    conn = get_app_db_connection()  # telehotwire DB
    cursor = conn.cursor(dictionary=True)

    offset = (page - 1) * limit

    query = """
       SELECT 
    id, sender_id, receiver_id, body,
    replied_to, sent_at, b_deleted, status,
    image_name, local_image_name
        FROM Messages
        WHERE 
            ((sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s))
            AND body != ''
        ORDER BY id ASC
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (uuid1, uuid2, uuid2, uuid1, limit, offset))
    rows = cursor.fetchall()

    formatted = []
    for row in rows:
        sent_at = row["sent_at"] or datetime.now()

        formatted.append({
            "id": str(row["id"]),
            "sender_id": row["sender_id"],
            "receiver_id": row["receiver_id"],
            "body": row["body"],
            "replied_to": row.get("replied_to"),
            "time": sent_at.strftime("%I:%M %p"),
            "day": sent_at.isoweekday(),
            "b_deleted": bool(row.get("b_deleted", False)),
            "status": row.get("status", 1),
            "image_name": row.get("image_name", ""),
            "local_image_name": row.get("local_image_name", ""),
            "date": sent_at.isoformat() + "Z"
        })


    cursor.close()
    conn.close()

    return {
        "code": 200,
        "success": True,
        "page": page,
        "limit": limit,
        "messages": formatted
    }

