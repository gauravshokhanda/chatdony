from app.db import get_app_db_connection

conn = get_app_db_connection()
if conn:
    print("✅ Connected to MySQL!")
else:
    print("❌ Connection failed.")
