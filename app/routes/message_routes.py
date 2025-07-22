from fastapi import APIRouter

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.get("/ping")
async def message_ping():
    return {"message": "Message service running"}
