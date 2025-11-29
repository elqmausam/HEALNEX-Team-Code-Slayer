# hospital_agent/api/routes/chat.py

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()




class Message(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message", min_length=1)
    conversation_history: List[Message] = Field(
        default=[],
        description="Previous conversation messages"
    )
    hospital_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current hospital context (occupancy, alerts, etc.)"
    )
    stream: bool = Field(
        default=False,
        description="Enable streaming response"
    )


class ChatResponse(BaseModel):
    status: str
    response: str
    conversation_id: Optional[str] = None
    provider: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    timestamp: str




@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, app_request: Request):
    """
    Chat with the AI hospital assistant
    
    Supports:
    - Medical queries
    - Hospital operations questions
    - Protocol lookup
    - General assistance
    """
    try:
        llm_service = app_request.app.state.llm_service
        cache_service = app_request.app.state.cache_service
        vector_service = app_request.app.state.vector_service
        
        # Format conversation history
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        
        # Check if question relates to protocols - use RAG
        if any(keyword in request.message.lower() 
               for keyword in ["protocol", "procedure", "guideline", "policy"]):
            
            # Search vector database for relevant protocols
            if vector_service and vector_service.initialized:
                relevant_docs = await vector_service.search_protocols(
                    query=request.message,
                    top_k=3
                )
                
                if relevant_docs:
                    # Add context to hospital_context
                    if request.hospital_context is None:
                        request.hospital_context = {}
                    request.hospital_context["relevant_protocols"] = [
                        {"title": doc["metadata"].get("title", "Unknown"),
                         "content": doc["text"][:500]}
                        for doc in relevant_docs
                    ]
        
        # Generate response
        response = await llm_service.generate_chat_response(
            user_message=request.message,
            conversation_history=history,
            hospital_context=request.hospital_context
        )
        
        return ChatResponse(
            status="success",
            response=response["response"],
            provider=response["provider"],
            model=response.get("model"),
            tokens_used=response.get("tokens_used"),
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest, app_request: Request):
    """
    Streaming chat endpoint for real-time responses
    Returns Server-Sent Events (SSE)
    """
    from fastapi.responses import StreamingResponse
    
    try:
        llm_service = app_request.app.state.llm_service
        
        # Format conversation history
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        
        async def generate():
            """Generator for streaming response"""
            try:
                async for chunk in llm_service.generate_streaming_response(
                    prompt=request.message,
                    conversation_history=history
                ):
                    # Format as Server-Sent Event
                    yield f"data: {chunk}\n\n"
                
                # Send completion signal
                yield "data: [DONE]\n\n"
            
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: ERROR: {str(e)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    app_request: Request
):
    """
    Retrieve conversation history
    (Placeholder - implement with database)
    """
    cache_service = app_request.app.state.cache_service
    
    try:
        # Try to get from cache
        if cache_service:
            history = await cache_service.get(f"conversation:{conversation_id}")
            if history:
                return {
                    "status": "success",
                    "conversation_id": conversation_id,
                    "messages": history
                }
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "messages": [],
            "note": "Conversation history not found or expired"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    app_request: Request
):
    """Clear conversation history"""
    cache_service = app_request.app.state.cache_service
    
    try:
        if cache_service:
            await cache_service.delete(f"conversation:{conversation_id}")
        
        return {
            "status": "success",
            "message": f"Conversation {conversation_id} cleared"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-ask")
async def quick_ask(
    question: str,
    app_request: Request
):
    """
    Quick single question without conversation context
    Useful for simple queries
    """
    try:
        llm_service = app_request.app.state.llm_service
        
        response = await llm_service.generate_response(
            prompt=question,
            system_prompt="You are a helpful hospital assistant. Provide concise, accurate answers."
        )
        
        return {
            "status": "success",
            "question": question,
            "answer": response["response"],
            "provider": response["provider"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_suggestions(context: Optional[str] = None):
    """
    Get suggested questions based on context
    Helps users know what they can ask
    """
    
    suggestions = {
        "general": [
            "What is the current bed occupancy rate?",
            "How many patients are in the ER?",
            "What are today's predicted admissions?",
            "Show me the emergency triage protocol",
            "What factors affect admission rates?"
        ],
        "emergency": [
            "What is the emergency triage protocol?",
            "How to handle a cardiac emergency?",
            "What is the rapid response team procedure?",
            "Infection control during emergencies"
        ],
        "operations": [
            "How to optimize bed allocation?",
            "Staff scheduling best practices",
            "Patient discharge workflow",
            "Bed turnover optimization"
        ],
        "predictions": [
            "What is the forecast for tomorrow?",
            "When is the next surge expected?",
            "What factors are affecting admissions today?",
            "Historical admission patterns"
        ]
    }
    
    if context and context in suggestions:
        return {
            "status": "success",
            "context": context,
            "suggestions": suggestions[context]
        }
    
    return {
        "status": "success",
        "suggestions": suggestions
    }