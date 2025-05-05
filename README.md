# SimpleAgent

A powerful document processing and question-answering system with AI agents and web search capabilities. SimpleAgent allows you to upload documents, query their content, and get AI-assisted responses with source attribution.

## Features

- **Document Processing**: Upload and process PDF documents with automatic text extraction and vectorization
- **Intelligent Querying**: Ask questions about your documents using natural language
- **Multi-Agent System**: Utilizes specialized AI agents for research, writing, and validation
- **Web Search Integration**: Optionally search the web to supplement document information
- **Conversation History**: Save and retrieve conversation history for future reference
- **React Frontend**: User-friendly interface for easy interaction with the system

## Architecture

SimpleAgent consists of:

### Backend API Server
FastAPI-based service providing document processing and querying endpoints

### Multi-Agent System
Specialized AI agents for different tasks:
- **Research Agent**: Searches documents for relevant information
- **Web Search Agent**: Finds information from the internet
- **Writing Agent**: Crafts clear and informative responses
- **Validation Agent**: Reviews information for accuracy

### Components
- **Vector Database**: FAISS-based document indexing for efficient similarity search
- **SQL Database**: Stores document metadata, chunks, and conversation history
- **React Frontend**: Web interface for document upload, querying, and viewing results

## API Endpoints

- `POST /upload`: Upload a PDF document
- `GET /documents`: List all uploaded documents
- `POST /query`: Query documents with AI
- `POST /combined-query`: Query documents and optionally search the web
- `POST /conversations`: Create a new conversation
- `GET /conversations`: List all conversations
- `GET /conversations/{conversation_id}`: Get messages from a conversation
- `POST /conversations/{conversation_id}/messages`: Add a message to a conversation

## Project Structure

```
simpleagent/
├── agents.py               # AI agents implementation
├── database.py            # Database operations
├── document_processor.py  # PDF processing and vectorization
├── main.py               # FastAPI server and endpoints
├── memory.py             # Conversation memory implementation
├── schemas.py            # Pydantic models for request/response
├── web_search.py         # Web search functionality
├── requirements.txt      # Python dependencies
├── uploads/             # Uploaded documents storage
├── indices/             # FAISS vector indices
└── document-agent-app/  # React frontend
    ├── src/
    │   ├── components/  # React components
    │   ├── App.js       # Main application component
    │   └── api.js       # API client
    └── package.json     # Frontend dependencies
```

## How It Works

1. **Document Upload**: Upload a PDF document through the web interface or API
2. **Document Processing**: The system extracts text, splits it into chunks, and creates vectorized embeddings
3. **Query Processing**:
   - Your natural language query is processed by specialized AI agents
   - The Research Agent searches document chunks for relevant information
   - Optionally, the Web Search Agent searches the internet for supplementary information
   - The Writing Agent crafts a comprehensive response
   - The Validation Agent checks for accuracy and consistency
4. **Response**: The system returns a well-structured response with source attribution