

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncGenerator
import logging
import os

from .core.config import settings
from .api.routes import chat, predictions, memory, voice, documents
from .api.routes import demo  # Demo endpoint for free APIs
from .api.routes import mock_hmis, mock_lab  # Mock hospital data APIs
from .api.routes import multi_agent  # NEW: Multi-agent coordination
from .services.llm_service import LLMService
from .services.vector_service import VectorService
from .services.prediction_service import PredictionService
from .services.cache_service import CacheService
from .services.monitoring_service import MonitoringService
from .services.langgraph_negotiation_service import LangGraphNegotiationService
from .services.multi_agent_service import MultiAgentCoordinationService  # NEW
from .api.routes import autonomous_negotiation
from .api.routes import documents_extended

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
llm_service: LLMService = None
vector_service: VectorService = None
prediction_service: PredictionService = None
cache_service: CacheService = None
monitoring_service: MonitoringService = None
multi_agent_service: MultiAgentCoordinationService = None  # NEW


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services"""
    global llm_service, vector_service, prediction_service, cache_service, monitoring_service, multi_agent_service
    
    logger.info("Initializing Hospital Agent services...")
    
    # Initialize services with connection pooling
    cache_service = CacheService()
    await cache_service.initialize()
    
    vector_service = VectorService()
    await vector_service.initialize()
    
    llm_service = LLMService()
    #await llm_service.initialize()
    
    prediction_service = PredictionService(
        cache_service=cache_service,
        vector_service=vector_service
    )
    await prediction_service.initialize()
    
    monitoring_service = MonitoringService()
    
    # Initialize LangGraph negotiation service
    langgraph_service = LangGraphNegotiationService(cache_service=cache_service)
    await langgraph_service.initialize()
    
    # NEW: Initialize Multi-Agent Coordination Service (The Parliament)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found! Multi-agent system requires OpenAI API.")
        raise ValueError("OPENAI_API_KEY is required for multi-agent coordination")
    
    multi_agent_service = MultiAgentCoordinationService(openai_api_key=openai_api_key)
    logger.info("Multi-Agent Coordination Service (The Parliament) initialized with 3 demo hospitals")
    
    # Store in app state
    app.state.llm_service = llm_service
    app.state.vector_service = vector_service
    app.state.prediction_service = prediction_service
    app.state.cache_service = cache_service
    app.state.monitoring_service = monitoring_service
    app.state.langgraph_service = langgraph_service
    app.state.multi_agent_service = multi_agent_service  # NEW
    
    logger.info("All services initialized successfully")
    logger.info("=" * 60)
    logger.info("🤖 THE PARLIAMENT IS NOW IN SESSION")
    logger.info("=" * 60)
    logger.info("Available Hospital Agents:")
    for agent_id, agent_info in multi_agent_service.get_all_agents().items():
        logger.info(f"  - {agent_info['name']} ({agent_id})")
    logger.info("=" * 60)
    
    yield
    
    # Cleanup
    logger.info("Shutting down services...")
    await cache_service.close()
    await vector_service.close()
    await llm_service.close()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Hospital Agent API with Multi-Agent Coordination",
    description="AI-powered hospital management with autonomous inter-hospital negotiations",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
# CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Include routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
#app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["demo"])
app.include_router(mock_hmis.router, prefix="/api/v1/mock/hmis", tags=["mock-hmis"])
app.include_router(mock_lab.router, prefix="/api/v1/mock/lab", tags=["mock-lab"])
app.include_router(
    autonomous_negotiation.router,
    prefix="/api/v1/autonomous-negotiation",
    tags=["autonomous-negotiation"]
)
# NEW: Multi-Agent Coordination Routes
app.include_router(
    multi_agent.router, 
    prefix="/api/v1/parliament", 
    tags=["multi-agent-coordination"]
)
app.include_router(
    documents_extended.router,
    prefix="/api/v1",
    tags=["documents-extended"]
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Hospital Agent with Multi-Agent Coordination",
        "version": "2.0.0",
        "features": [
            "AI Chat",
            "Predictive Analytics",
            "Voice Processing",
            "Document Management",
            "Multi-Agent Coordination (The Parliament)"
        ]
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    services_status = {
        "llm": await llm_service.health_check() if llm_service else False,
        "vector_db": await vector_service.health_check() if vector_service else False,
        "cache": await cache_service.health_check() if cache_service else False,
        "multi_agent": multi_agent_service is not None
    }
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status,
        "parliament_agents": len(multi_agent_service.agents) if multi_agent_service else 0,
        "active_negotiations": len(multi_agent_service.sessions) if multi_agent_service else 0,
        "timestamp": monitoring_service.get_timestamp() if monitoring_service else None
    }


@app.get("/parliament/status")
async def parliament_status():
    """Get real-time status of The Parliament"""
    if not multi_agent_service:
        raise HTTPException(status_code=503, detail="Multi-agent service not initialized")
    
    agents_info = []
    for agent_id, agent in multi_agent_service.agents.items():
        agents_info.append({
            "id": agent.hospital_id,
            "name": agent.hospital_name,
            "personality": agent.personality,
            "resources": agent.hospital_data.get("resources", {}),
            "occupancy": agent.hospital_data.get("occupancy", 0),
            "status": "online"
        })
    
    return {
        "parliament_status": "active",
        "total_agents": len(multi_agent_service.agents),
        "active_negotiations": len(multi_agent_service.sessions),
        "agents": agents_info
    }


@app.websocket("/ws/chat/{hospital_id}")
async def websocket_chat(websocket: WebSocket, hospital_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # Process with streaming
            async for chunk in llm_service.stream_chat(
                message=message,
                hospital_id=hospital_id,
                context=data.get("context", {})
            ):
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk
                })
            
            # Send completion signal
            await websocket.send_json({"type": "complete"})
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 70)
    print("🏥 HOSPITAL AGENT - MULTI-AGENT COORDINATION SYSTEM")
    print("=" * 70)
    print("Starting The Parliament...")
    print("3 AI Hospital Agents ready for autonomous negotiations")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=1,  # Single worker for demo to maintain state
        log_level="info"
    )