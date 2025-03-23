# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import shutil
import os
from typing import List
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# For delievering index.html file imports
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pdf_processor import process_pdfs, get_answer_from_pdfs

app = FastAPI(title="PDF Q&A API", description="API for PDF document question answering using Gemini")

app.mount("/static", StaticFiles(directory="static"), name="static")



class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get('content-length'):
            content_length = int(request.headers.get('content-length', 0))
            max_size = 25 * 1024 * 1024  # 25MB in bytes
            if content_length > max_size:
                return Response(status_code=413, content="Request too large")
        return await call_next(request)

MAX_TOTAL_SIZE_MB = 20  # Limit set to 20MB
MAX_TOTAL_SIZE_BYTES = MAX_TOTAL_SIZE_MB * 1024 * 1024  # Convert MB to bytes
UPLOAD_DIR = "uploads"

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers

)
app.add_middleware(MaxBodySizeMiddleware)


# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Store processing status
processing_status = {"status": "idle", "message": ""}

def delete_existing_files():
    """Delete all previously uploaded files."""
    if os.path.exists(UPLOAD_DIR):
        for file_name in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)


@app.post("/upload-pdfs/")
async def upload_pdfs(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """
    Upload multiple PDF files, enforce a 20MB size limit, and process them in the background.
    """



    # Validate input
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Calculate total file size
    total_size = sum(file.size for file in files)
    if total_size > MAX_TOTAL_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"Total file size exceeds {MAX_TOTAL_SIZE_MB}MB limit")

    # Validate file types
    for file in files:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")


    # Delete previously uploaded files
    delete_existing_files()

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save new files
    file_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_paths.append(file_path)

    # Process PDFs in the background
    global processing_status
    processing_status = {"status": "processing", "message": "Processing PDFs..."}
    
    # Start processing in the background
    background_tasks.add_task(process_pdfs, file_paths, processing_status)

    return JSONResponse(
        content={
            "message": "Files uploaded successfully. Processing started.",
            "files": [file.filename for file in files],
            "status": processing_status["status"]
        }
    )

@app.get("/processing-status/")
async def get_processing_status():
    """
    Get the current PDF processing status.
    """
    return processing_status

@app.post("/ask-question/")
async def ask_question(question: str = Form(...)):
    """
    Ask a question about the previously uploaded PDFs.
    """
    if processing_status["status"] != "completed":
        return JSONResponse(
            status_code=400,
            content={
                "message": "PDF processing not completed. Current status: " + processing_status["status"],
                "status": processing_status["status"]
            }
        )
    
    try:
        answer = get_answer_from_pdfs(question)
        return {"question": question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)