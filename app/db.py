# app/db.py
import mysql.connector
from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, APP_DB_NAME, OPENFIRE_DB_NAME

def get_app_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=APP_DB_NAME
    )

def get_openfire_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=OPENFIRE_DB_NAME
    )
