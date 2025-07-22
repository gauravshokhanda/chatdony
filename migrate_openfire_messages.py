import traceback
from datetime import datetime
from app.db import get_app_db_connection, get_openfire_db_connection

def migrate_messages():
    try:
        openfire_db = get_openfire_db_connection()
        telehotwire_db = get_app_db_connection()

        of_cursor = openfire_db.cursor()
        th_cursor = telehotwire_db.cursor()

        print("📥 Fetching messages from Openfire...")
        of_cursor.execute("SELECT messageID, fromJID, toJID, body, sentDate FROM ofMessageArchive")
        rows = of_cursor.fetchall()
        print(f"✅ Total messages fetched: {len(rows)}")

        insert_query = """
        INSERT INTO Messages (
            sender_id, receiver_id, body, replied_to, image_name, local_image_name,
            b_deleted, status, message_type, file_url, file_type, sent_at
        ) VALUES (%s, %s, %s, NULL, '', '', FALSE, 1, 'message', NULL, NULL, %s)
        """

        for i, row in enumerate(rows):
            try:
                message_id, from_jid, to_jid, body, sent_date = row
                sender_id = from_jid.split('@')[0]
                receiver_id = to_jid.split('@')[0]
                sent_datetime = datetime.utcfromtimestamp(sent_date / 1000)

                th_cursor.execute(insert_query, (
                    sender_id,
                    receiver_id,
                    body,
                    sent_datetime
                ))

                if (i + 1) % 100 == 0:
                    print(f"📦 Migrated {i + 1} messages...")

            except Exception as inner_error:
                print(f"\n❌ Error migrating message {i + 1} (ID: {row[0]}):")
                traceback.print_exc()
                print("🚫 Migration stopped.")
                break

        telehotwire_db.commit()
        print("✅ Migration completed successfully.")

    except Exception as e:
        print("\n🔥 Fatal error during migration:")
        traceback.print_exc()

    finally:
        try:
            of_cursor.close()
            openfire_db.close()
            th_cursor.close()
            telehotwire_db.close()
        except:
            pass


if __name__ == "__main__":
    migrate_messages()
