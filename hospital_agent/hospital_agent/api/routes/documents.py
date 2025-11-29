

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    status: str
    document_id: str
    filename: str
    size_bytes: int
    content_type: str
    processed: bool
    timestamp: str


class DocumentQuery(BaseModel):
    query: str = Field(..., description="Search query", min_length=1)
    document_types: Optional[List[str]] = Field(default=None, description="Filter by document types")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")


class ProtocolUpdate(BaseModel):
    protocol_id: str = Field(..., description="Protocol identifier")
    title: str = Field(..., description="Protocol title")
    content: str = Field(..., description="Protocol content/text")
    category: str = Field(default="general", description="Protocol category")
    metadata: Optional[Dict[str, Any]] = None


# ============================================
# Endpoints
# ============================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    document_type: str = Form(default="general", description="Document type: protocol, policy, report, etc."),
    description: Optional[str] = Form(default=None, description="Document description"),
    app_request: Request = None
):
    """
    Upload and process a document
    
    Supports:
    - Medical protocols (PDF, DOCX)
    - Hospital policies
    - Research papers
    - Clinical guidelines
    
    The document will be:
    1. Stored
    2. Text extracted
    3. Indexed in vector database for semantic search
    """
    try:
        # Validate file type
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown"
        ]
        
        allowed_extensions = [".pdf", ".doc", ".docx", ".txt", ".md"]
        
        file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        
        if file.content_type not in allowed_types and file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: PDF, DOC, DOCX, TXT, MD"
            )
        
        # Read file
        file_data = await file.read()
        
        if len(file_data) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size: 50MB"
            )
        
        # Generate document ID
        doc_hash = hashlib.sha256(file_data).hexdigest()[:16]
        document_id = f"doc_{doc_hash}"
        
        # Extract text (mock - in production use PyPDF2, python-docx, etc.)
        extracted_text = f"Extracted text from {file.filename}"
        
        # Store in vector database if available
        vector_service = app_request.app.state.vector_service
        if vector_service and vector_service.initialized:
            await vector_service.upsert_document(
                doc_id=document_id,
                text=extracted_text,
                metadata={
                    "filename": file.filename,
                    "document_type": document_type,
                    "description": description,
                    "uploaded_at": datetime.now().isoformat(),
                    "size_bytes": len(file_data)
                }
            )
            processed = True
        else:
            processed = False
            logger.warning("Vector service unavailable - document not indexed")
        
        return DocumentUploadResponse(
            status="success",
            document_id=document_id,
            filename=file.filename,
            size_bytes=len(file_data),
            content_type=file.content_type,
            processed=processed,
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(query: DocumentQuery, app_request: Request):
    """
    Semantic search across uploaded documents
    
    Uses vector similarity to find relevant documents
    Great for finding protocols, policies, or specific procedures
    """
    try:
        vector_service = app_request.app.state.vector_service
        
        if not vector_service or not vector_service.initialized:
            return {
                "status": "unavailable",
                "message": "Document search unavailable - vector service not initialized",
                "results": []
            }
        
        # Search vector database
        results = await vector_service.search(
            query=query.query,
            top_k=query.top_k,
            filter_metadata={"document_type": query.document_types[0]} if query.document_types else None
        )
        
        return {
            "status": "success",
            "query": query.query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Document search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}")
async def get_document(document_id: str, app_request: Request):
    """
    Retrieve document details
    """
    try:
        # In production, retrieve from storage
        # For now, return mock data
        
        return {
            "status": "success",
            "document_id": document_id,
            "filename": "sample_protocol.pdf",
            "document_type": "protocol",
            "uploaded_at": datetime.now().isoformat(),
            "size_bytes": 245680,
            "description": "Emergency triage protocol"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{document_id}")
async def delete_document(document_id: str, app_request: Request):
    """
    Delete a document
    """
    try:
        vector_service = app_request.app.state.vector_service
        
        if vector_service and vector_service.initialized:
            await vector_service.delete_document(document_id)
        
        return {
            "status": "success",
            "message": f"Document {document_id} deleted",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/protocols/add")
async def add_protocol(protocol: ProtocolUpdate, app_request: Request):
    """
    Add or update a hospital protocol
    Protocols are stored in the vector database for quick retrieval
    """
    try:
        vector_service = app_request.app.state.vector_service
        
        if not vector_service or not vector_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Vector service unavailable"
            )
        
        # Store protocol
        success = await vector_service.upsert_document(
            doc_id=protocol.protocol_id,
            text=protocol.content,
            metadata={
                "title": protocol.title,
                "category": "protocol",
                "type": protocol.category,
                "updated_at": datetime.now().isoformat(),
                **(protocol.metadata or {})
            }
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Protocol {protocol.protocol_id} added/updated",
                "protocol_id": protocol.protocol_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store protocol")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Protocol add error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/protocols/search")
async def search_protocols(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
    app_request: Request = None
):
    """
    Search for specific protocols
    Example: "emergency triage", "infection control", "surgical prep"
    """
    try:
        vector_service = app_request.app.state.vector_service
        
        if not vector_service or not vector_service.initialized:
            return {
                "status": "unavailable",
                "message": "Protocol search unavailable",
                "protocols": []
            }
        
        # Search protocols
        results = await vector_service.search_protocols(
            query=query,
            protocol_type=category,
            top_k=top_k
        )
        
        return {
            "status": "success",
            "query": query,
            "category": category,
            "protocols": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/protocols/list")
async def list_protocols(
    category: Optional[str] = None,
    limit: int = 20,
    app_request: Request = None
):
    """
    List all available protocols
    """
    try:
        vector_service = app_request.app.state.vector_service
        
        if not vector_service or not vector_service.initialized:
            return {
                "status": "unavailable",
                "protocols": []
            }
        
        # Get protocol stats
        stats = await vector_service.get_stats()
        
        # In production, query all protocols from vector DB
        # For now, return mock data
        protocols = [
            {
                "protocol_id": "protocol_001",
                "title": "Emergency Triage Protocol",
                "category": "emergency",
                "last_updated": datetime.now().isoformat()
            },
            {
                "protocol_id": "protocol_002",
                "title": "Infection Control Protocol",
                "category": "infection_control",
                "last_updated": datetime.now().isoformat()
            },
            {
                "protocol_id": "protocol_003",
                "title": "Patient Admission Protocol",
                "category": "admission",
                "last_updated": datetime.now().isoformat()
            }
        ]
        
        return {
            "status": "success",
            "protocols": protocols,
            "total_count": len(protocols),
            "vector_db_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-text")
async def extract_text(
    file: UploadFile = File(...),
    app_request: Request = None
):
    """
    Extract text from a document without storing it
    Useful for preview or one-time text extraction
    """
    try:
        file_data = await file.read()
        
        # Mock text extraction (in production, use proper libraries)
        extracted = f"Extracted text from {file.filename}:\n\nThis is sample extracted text content."
        
        return {
            "status": "success",
            "filename": file.filename,
            "text": extracted,
            "char_count": len(extracted),
            "word_count": len(extracted.split()),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_document(
    file: UploadFile = File(...),
    max_length: int = Form(default=200, description="Maximum summary length in words"),
    app_request: Request = None
):
    """
    Generate an AI summary of a document
    Great for quickly understanding long protocols or reports
    """
    try:
        file_data = await file.read()
        
        # Extract text (mock)
        extracted_text = "Long document text here..."
        
        # Generate summary with LLM
        llm_service = app_request.app.state.llm_service
        
        summary = await llm_service.generate_response(
            prompt=f"""Summarize this document in {max_length} words or less:

{extracted_text}

Provide a clear, concise summary highlighting key points.""",
            system_prompt="You are a medical document summarization assistant."
        )
        
        return {
            "status": "success",
            "filename": file.filename,
            "summary": summary["response"],
            "original_length": len(extracted_text.split()),
            "summary_length": len(summary["response"].split()),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Document summarization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_document_stats(app_request: Request):
    """
    Get document repository statistics
    """
    try:
        vector_service = app_request.app.state.vector_service
        
        if not vector_service or not vector_service.initialized:
            return {
                "status": "unavailable",
                "message": "Document statistics unavailable"
            }
        
        stats = await vector_service.get_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))