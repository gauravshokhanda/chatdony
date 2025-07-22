from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
import os

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "application/pdf"]

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, and PDF files are allowed.")
        
        filename = f"{uuid4()}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        # Save the file to disk
        with open(filepath, "wb") as buffer:
            buffer.write(await file.read())
            print(f"File saved at: {filepath}")

        file_url = f"/uploads/{filename}"
        return JSONResponse({
            "file_url": file_url,
            "file_type": file.content_type
        })
    
    except HTTPException as http_exc:
        raise http_exc  # Raise the HTTPException if it's raised due to invalid file type
    except Exception as e:
        # Log the error for debugging
        print(f"Error while uploading file: {e}")
        return JSONResponse(status_code=500, content={"error": "File upload failed", "details": str(e)})

