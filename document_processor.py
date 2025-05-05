import uuid
import os
from typing import List, Dict, Optional
import asyncio
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai.embeddings import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from database import update_document_status, add_chunk, get_document, get_document_chunks
import numpy as np
import faiss
import pickle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize embeddings
embeddings = AzureOpenAIEmbeddings(
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
        deployment="text-embedding-ada-002",  # Make sure this deployment exists in your Azure OpenAI resource
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

# Path to store FAISS indices
INDEX_PATH = "indices"
os.makedirs(INDEX_PATH, exist_ok=True)

async def process_document(doc_id: str, file_path: str):
    try:
        # Extract text from PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        
        # Store chunks in database
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            content = chunk.page_content
            metadata = {
                "page": chunk.metadata.get("page", 0),
                "source": file_path
            }
            await add_chunk(chunk_id, doc_id, content, metadata)
        
        # Create embeddings and store in FAISS index
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [{"chunk_id": str(uuid.uuid4()), "doc_id": doc_id, "page": chunk.metadata.get("page", 0)} for chunk in chunks]
        
        # Create FAISS index
        vectorstore = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        
        # Save index
        index_path = os.path.join(INDEX_PATH, f"{doc_id}.pkl")
        vectorstore.save_local(index_path)
        
        # Update document status
        await update_document_status(doc_id, "processed", {"chunk_count": len(chunks)})
        
        return {"status": "success", "chunks": len(chunks)}
    except Exception as e:
        await update_document_status(doc_id, "error", {"error": str(e)})
        return {"status": "error", "error": str(e)}

async def query_documents(query: str, doc_ids: Optional[List[str]] = None):
    if not doc_ids:
        return {"results": [], "error": "No documents specified"}
    
    combined_results = []
    
    for doc_id in doc_ids:
        index_path = os.path.join(INDEX_PATH, f"{doc_id}.pkl")
        if not os.path.exists(index_path):
            continue
        
        # Load the index
        vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        
        # Search for similar documents
        results = vectorstore.similarity_search_with_score(query, k=5)
        
        # Get document info
        doc = await get_document(doc_id)
        
        # Format results
        for doc_chunk, score in results:
            combined_results.append({
                "doc_id": doc_id,
                "title": doc.get("title", "Unknown"),
                "content": doc_chunk.page_content,
                "page": doc_chunk.metadata.get("page", 0),
                "score": float(score),
                "source": doc.get("path", "Unknown")
            })
    
    # Sort by relevance score
    combined_results.sort(key=lambda x: x["score"])
    
    return {"results": combined_results}