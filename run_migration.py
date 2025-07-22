from app.db import get_app_db_connection

def run_sql_file(filepath):
    with open(filepath, 'r') as f:
        sql = f.read()

    conn = get_app_db_connection()
    if not conn:
        print("❌ DB connection failed")
        return

    cursor = conn.cursor()
    for statement in sql.split(';'):
        stmt = statement.strip()
        if stmt:
            try:
                print(f"➡ Executing: {stmt[:60]}...")
                cursor.execute(stmt)
            except Exception as e:
                print(f"⚠️ Skipping due to error: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Migration completed (with skips if needed).")

if __name__ == "__main__":
    run_sql_file("migrations/migration_001.sql")
