from fastapi import APIRouter
from app.services import get_user_status

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/ping")
async def user_ping():
    return {"message": "User service running"}

@router.get("/status/{user_id}")
def status(user_id: int):
    status = get_user_status(user_id)
    return status or {"error": "User not found"}
