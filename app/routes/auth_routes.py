from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import timedelta, date
from app.db import get_app_db_connection
from app.utils.auth_utils import get_password_hash, create_access_token,verify_password


router = APIRouter()

class SignUpSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str
    date_of_birth: date


@router.post("/signup", tags=["Auth"])
def signup(user: SignUpSchema):
    conn = get_app_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)

    try:
        # Check email
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Check username
        cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already taken")

        # Hash and insert
        hashed_pw = get_password_hash(user.password)
        cursor.execute(
            "INSERT INTO users (username, email, password, display_name, date_of_birth) VALUES (%s, %s, %s, %s, %s)",
            (user.username, user.email, hashed_pw, user.display_name, user.date_of_birth)
        )
        conn.commit()

        # Fetch full user record
        cursor.execute("SELECT user_id, username, email, display_name, date_of_birth FROM users WHERE email = %s", (user.email,))
        user_data = cursor.fetchone()

        token = create_access_token(
            data={"sub": str(user_data["user_id"])},
            expires_delta=timedelta(minutes=60)
        )

        return {
            "success": True,
            "message": "User created successfully",
            "token": token,
            "user": user_data
        }

    finally:
        cursor.close()
        conn.close()




class LoginSchema(BaseModel):
    email: EmailStr
    password: str

@router.post("/login", tags=["Auth"])
def login(user: LoginSchema):
    conn = get_app_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)

    try:
        # Check user
        cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(user.password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Incorrect password")

        token = create_access_token(
            data={"sub": str(db_user["user_id"])},
            expires_delta=timedelta(minutes=60)
        )

        # Remove password before sending
        db_user.pop("password")

        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": db_user
        }

    finally:
        cursor.close()
        conn.close()
