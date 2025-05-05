from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import json
from typing import List, Dict, Optional
import uuid

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

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    msg_metadata = Column(Text)  # JSON string for additional data like sources, validation, etc.
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")

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

async def create_conversation(title: str) -> str:
    """Create a new conversation and return its ID."""
    conversation_id = str(uuid.uuid4())
    async with async_session() as session:
        new_conversation = Conversation(id=conversation_id, title=title)
        session.add(new_conversation)
        await session.commit()
    return conversation_id

async def add_message(conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> str:
    """Add a message to a conversation and return its ID."""
    message_id = str(uuid.uuid4())
    metadata_str = json.dumps(metadata) if metadata else None
    
    async with async_session() as session:
        new_message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            msg_metadata=metadata_str
        )
        session.add(new_message)
        await session.commit()
    
    return message_id

async def get_conversation_messages(conversation_id: str) -> List[Dict]:
    """Get all messages for a specific conversation."""
    async with async_session() as session:
        from sqlalchemy import select
        query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        result = await session.execute(query)
        messages = result.scalars().all()
        
        return [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "metadata": json.loads(message.msg_metadata) if message.msg_metadata else None,
                "created_at": message.created_at.isoformat() if message.created_at else None
            }
            for message in messages
        ]

async def get_conversations() -> List[Dict]:
    """Get all conversations."""
    async with async_session() as session:
        from sqlalchemy import select
        query = select(Conversation).order_by(Conversation.updated_at.desc())
        result = await session.execute(query)
        conversations = result.scalars().all()
        
        return [
            {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
            }
            for conversation in conversations
        ]