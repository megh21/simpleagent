from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import json
from typing import List, Dict, Optional

# SQLite database URL
DATABASE_URL = "sqlite+aiosqlite:///document_agents.db"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    path = Column(String, nullable=False)
    status = Column(String, default="pending")
    doc_metadata = Column(Text)  # Renamed from 'metadata' to avoid SQLAlchemy reserved name
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationship to chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(String, primary_key=True)
    doc_id = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column(Text)  # Renamed from 'metadata' to avoid SQLAlchemy reserved name
    
    # Relationship to document
    document = relationship("Document", back_populates="chunks")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def add_document(doc_id: str, title: str, path: str):
    async with async_session() as session:
        new_doc = Document(id=doc_id, title=title, path=path)
        session.add(new_doc)
        await session.commit()

async def update_document_status(doc_id: str, status: str, metadata: Optional[Dict] = None):
    async with async_session() as session:
        from sqlalchemy import select
        query = select(Document).where(Document.id == doc_id)
        result = await session.execute(query)
        doc = result.scalar_one_or_none()
        
        if doc:
            doc.status = status
            if metadata:
                doc.doc_metadata = json.dumps(metadata)
            await session.commit()

async def add_chunk(chunk_id: str, doc_id: str, content: str, metadata: Optional[Dict] = None):
    async with async_session() as session:
        metadata_str = json.dumps(metadata) if metadata else None
        new_chunk = Chunk(id=chunk_id, doc_id=doc_id, content=content, chunk_metadata=metadata_str)
        session.add(new_chunk)
        await session.commit()

async def get_document(doc_id: str):
    async with async_session() as session:
        from sqlalchemy import select
        query = select(Document).where(Document.id == doc_id)
        result = await session.execute(query)
        doc = result.scalar_one_or_none()
        
        if doc:
            doc_dict = {
                "id": doc.id,
                "title": doc.title,
                "path": doc.path,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            
            if doc.doc_metadata:
                try:
                    doc_dict["metadata"] = json.loads(doc.doc_metadata)
                except:
                    doc_dict["metadata"] = {}
                    
            return doc_dict
        return None

async def get_all_documents():
    async with async_session() as session:
        from sqlalchemy import select
        query = select(Document).order_by(Document.created_at.desc())
        result = await session.execute(query)
        docs = result.scalars().all()
        
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in docs
        ]

async def get_document_chunks(doc_id: str):
    async with async_session() as session:
        from sqlalchemy import select
        query = select(Chunk).where(Chunk.doc_id == doc_id)
        result = await session.execute(query)
        chunks = result.scalars().all()
        
        return [
            {
                "id": chunk.id,
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "metadata": json.loads(chunk.chunk_metadata) if chunk.chunk_metadata else {}
            }
            for chunk in chunks
        ]