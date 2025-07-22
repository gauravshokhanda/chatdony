from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.websocket.websocket_server import websocket_app
from app.routes.user_routes import router as user_router
from fastapi.staticfiles import StaticFiles
from app.routes.upload_routes import router as upload_router

from app.routes import (
    user_routes,
    chat_routes,
    conversation_routes,
    message_routes,
    auth_routes
)
app = FastAPI(
    title="Real-Time Chat API",
    docs_url="/api-docs",       # 👈 this replaces /docs
    redoc_url="/api-redoc",     # 👈 this replaces /redoc
    openapi_url="/openapi.json" # 👈 default OpenAPI schema
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket mount
websocket_app(app)  # Mount the Socket.IO or custom WebSocket logic

# Register API routes with tags
@app.get("/")
def read_root():
    return {"status": "Backend is working fine ✅"}



app.include_router(user_routes, tags=["Users"])
app.include_router(chat_routes, tags=["Chat"])
app.include_router(conversation_routes, tags=["Conversations"])
app.include_router(message_routes, tags=["Messages"])
app.include_router(user_router)
app.include_router(upload_router, tags=["Uploads"])
app.include_router(auth_routes.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")