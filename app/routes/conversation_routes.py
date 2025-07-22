from fastapi import APIRouter

router = APIRouter(prefix="/conversation", tags=["Conversation"])

@router.get("/ping")
async def conversation_ping():
    return {"message": "Conversation service running"}
