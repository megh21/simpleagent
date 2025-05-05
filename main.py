from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import uuid
from database import init_db, add_document, get_document, get_all_documents
from document_processor import process_document, query_documents
from agents import execute_agents_parallel

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    await init_db()

class QueryRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...)
):
    # Generate unique ID for the document
    doc_id = str(uuid.uuid4())
    
    # Save file locally
    file_path = f"uploads/{doc_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Add document to database
    await add_document(doc_id, title, file_path)
    
    # Process document in background
    background_tasks.add_task(process_document, doc_id, file_path)
    
    return {"doc_id": doc_id, "title": title, "status": "processing"}

@app.get("/documents")
async def get_documents():
    docs = await get_all_documents()
    return {"documents": docs}

@app.post("/query")
async def query(request: QueryRequest):
    # Execute agents in parallel to analyze documents and answer the query
    result = await execute_agents_parallel(request.query, request.doc_ids)
    return result

class CombinedQueryRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    include_web_search: bool = False

@app.post("/combined-query")
async def combined_query(request: CombinedQueryRequest):
    # Execute agents to analyze documents and web, and answer the query
    result = await execute_agents_parallel(
        request.query, 
        request.doc_ids, 
        request.include_web_search
    )
    return result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)