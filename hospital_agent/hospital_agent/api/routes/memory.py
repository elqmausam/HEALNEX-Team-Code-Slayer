# hospital_agent/api/routes/memory.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()




class MemoryItem(BaseModel):
    key: str = Field(..., description="Memory key identifier")
    value: Any = Field(..., description="Value to store")
    ttl: Optional[int] = Field(default=86400, description="Time to live in seconds (default: 24 hours)")
    category: Optional[str] = Field(default="general", description="Memory category")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MemoryQuery(BaseModel):
    keys: Optional[List[str]] = Field(default=None, description="Specific keys to retrieve")
    category: Optional[str] = Field(default=None, description="Filter by category")
    pattern: Optional[str] = Field(default=None, description="Search pattern (e.g., 'user:*')")


class ConversationMemory(BaseModel):
    user_id: str = Field(..., description="User identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    summary: str = Field(..., description="Conversation summary")
    key_points: List[str] = Field(default=[], description="Important points from conversation")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")




@router.post("/store")
async def store_memory(memory: MemoryItem, app_request: Request):
    """
    Store a memory item
    Can be used for:
    - User preferences
    - Session data
    - Temporary context
    - Conversation summaries
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Memory service unavailable"
            )
        
        # Add metadata
        stored_value = {
            "value": memory.value,
            "category": memory.category,
            "metadata": memory.metadata,
            "stored_at": datetime.now().isoformat()
        }
        
        # Store in cache
        success = await cache_service.set(
            key=f"memory:{memory.key}",
            value=stored_value,
            ttl=memory.ttl
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Memory stored: {memory.key}",
                "expires_in": memory.ttl,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store memory")
    
    except Exception as e:
        logger.error(f"Memory store error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve/{key}")
async def retrieve_memory(key: str, app_request: Request):
    """
    Retrieve a specific memory item
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Memory service unavailable"
            )
        
        memory = await cache_service.get(f"memory:{key}")
        
        if memory:
            return {
                "status": "success",
                "key": key,
                "data": memory,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Memory not found: {key}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_memories(query: MemoryQuery, app_request: Request):
    """
    Query multiple memory items
    Supports filtering by keys, category, or pattern
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            return {
                "status": "success",
                "memories": [],
                "count": 0,
                "note": "Memory service unavailable"
            }
        
        memories = {}
        
        # Query by specific keys
        if query.keys:
            for key in query.keys:
                memory = await cache_service.get(f"memory:{key}")
                if memory:
                    memories[key] = memory
        
        # Query by pattern
        elif query.pattern:
            pattern = f"memory:{query.pattern}"
            keys = await cache_service.get_keys(pattern)
            
            for full_key in keys:
                key = full_key.replace("memory:", "")
                memory = await cache_service.get(full_key)
                if memory:
                    # Filter by category if specified
                    if query.category:
                        if memory.get("category") == query.category:
                            memories[key] = memory
                    else:
                        memories[key] = memory
        
        return {
            "status": "success",
            "memories": memories,
            "count": len(memories),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Memory query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{key}")
async def delete_memory(key: str, app_request: Request):
    """
    Delete a specific memory item
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Memory service unavailable"
            )
        
        success = await cache_service.delete(f"memory:{key}")
        
        return {
            "status": "success",
            "message": f"Memory deleted: {key}",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/save")
async def save_conversation(memory: ConversationMemory, app_request: Request):
    """
    Save conversation summary and context
    Useful for maintaining conversation history
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Memory service unavailable"
            )
        
        conversation_data = {
            "user_id": memory.user_id,
            "conversation_id": memory.conversation_id,
            "summary": memory.summary,
            "key_points": memory.key_points,
            "context": memory.context,
            "saved_at": datetime.now().isoformat()
        }
        
        # Store conversation
        key = f"conversation:{memory.user_id}:{memory.conversation_id}"
        success = await cache_service.set(
            key=key,
            value=conversation_data,
            ttl=604800  # 7 days
        )
        
        if success:
            return {
                "status": "success",
                "message": "Conversation saved",
                "conversation_id": memory.conversation_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save conversation")
    
    except Exception as e:
        logger.error(f"Conversation save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{user_id}")
async def get_user_conversations(
    user_id: str,
    app_request: Request,
    limit: int = 10
    
):
    """
    Get all conversations for a user
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            return {
                "status": "success",
                "conversations": [],
                "count": 0
            }
        
        # Get all conversation keys for user
        pattern = f"conversation:{user_id}:*"
        keys = await cache_service.get_keys(pattern)
        
        conversations = []
        for key in keys[:limit]:
            conv = await cache_service.get(key)
            if conv:
                conversations.append(conv)
        
        return {
            "status": "success",
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_stats(app_request: Request):
    """
    Get memory system statistics
    Shows cache usage, hit rates, etc.
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            return {
                "status": "unavailable",
                "message": "Memory service not initialized"
            }
        
        stats = await cache_service.get_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-preferences")
async def store_user_preferences(
    user_id: str,
    preferences: Dict[str, Any],
    app_request: Request
):
    """
    Store user preferences
    Examples: UI settings, notification preferences, language, etc.
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            raise HTTPException(
                status_code=503,
                detail="Memory service unavailable"
            )
        
        pref_data = {
            "user_id": user_id,
            "preferences": preferences,
            "updated_at": datetime.now().isoformat()
        }
        
        success = await cache_service.set(
            key=f"preferences:{user_id}",
            value=pref_data,
            ttl=2592000  # 30 days
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Preferences saved for user {user_id}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-preferences/{user_id}")
async def get_user_preferences(user_id: str, app_request: Request):
    """
    Retrieve user preferences
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if not cache_service or not cache_service.initialized:
            return {
                "status": "success",
                "preferences": {},
                "note": "Using default preferences"
            }
        
        prefs = await cache_service.get(f"preferences:{user_id}")
        
        if prefs:
            return {
                "status": "success",
                "user_id": user_id,
                "preferences": prefs.get("preferences", {}),
                "updated_at": prefs.get("updated_at"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "success",
                "user_id": user_id,
                "preferences": {},
                "note": "No preferences found, using defaults"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))