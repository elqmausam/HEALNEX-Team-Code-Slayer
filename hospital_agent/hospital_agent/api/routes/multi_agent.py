

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class NegotiationRequest(BaseModel):
    """Request to start negotiation"""
    initiator_hospital_id: str
    resource_type: str  # "ventilators", "icu_beds", "pulmonologists", "nurses"
    quantity: int
    urgency: str  # "critical", "high", "medium", "low"
    duration_days: int
    max_budget: float
    additional_details: Optional[Dict] = None


class AgentStatusResponse(BaseModel):
    """Agent status response"""
    agent_id: str
    hospital_name: str
    status: str
    resources: Dict
    last_active: str


@router.post("/negotiate", response_class=StreamingResponse)
async def start_negotiation(request_data: NegotiationRequest, app_request: Request):
    """
    Start autonomous AI-to-AI negotiation
    Returns Server-Sent Events stream with real-time updates
    """
    
    try:
        multi_agent_service = app_request.app.state.multi_agent_service
        
        async def event_generator():
            """Generate SSE events"""
            try:
                async for event in multi_agent_service.initiate_negotiation(
                    initiator_hospital_id=request_data.initiator_hospital_id,
                    resource_type=request_data.resource_type,
                    quantity=request_data.quantity,
                    urgency=request_data.urgency,
                    duration_days=request_data.duration_days,
                    max_budget=request_data.max_budget,
                    additional_details=request_data.additional_details
                ):
                    yield f"data: {json.dumps(event)}\n\n"
                
                # Send completion event
                yield f"data: {json.dumps({'event': 'stream_complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"Negotiation stream error: {e}")
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_all_agents(app_request: Request):
    """Get all available hospital agents"""
    
    try:
        multi_agent_service = app_request.app.state.multi_agent_service
        agents = multi_agent_service.get_all_agents()
        
        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }
        
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
async def get_agent_details(agent_id: str, app_request: Request):
    """Get detailed information about a specific agent"""
    
    try:
        multi_agent_service = app_request.app.state.multi_agent_service
        
        if agent_id not in multi_agent_service.agents:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent = multi_agent_service.agents[agent_id]
        
        return {
            "success": True,
            "agent": {
                "id": agent.hospital_id,
                "name": agent.hospital_name,
                "personality": agent.personality,
                "data": agent.hospital_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str, app_request: Request):
    """Get negotiation session details"""
    
    try:
        multi_agent_service = app_request.app.state.multi_agent_service
        session = multi_agent_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "session": {
                "id": session.session_id,
                "status": session.status,
                "initiator": session.initiator_hospital,
                "participants": session.participant_hospitals,
                "request": {
                    "resource_type": session.request.resource_type,
                    "quantity": session.request.quantity,
                    "urgency": session.request.urgency,
                    "max_budget": session.request.max_price
                },
                "offers_count": len(session.offers),
                "messages_count": len(session.messages),
                "final_agreement": session.final_agreement,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_all_sessions(app_request: Request):
    """Get all negotiation sessions"""
    
    try:
        multi_agent_service = app_request.app.state.multi_agent_service
        
        sessions = []
        for session_id, session in multi_agent_service.sessions.items():
            sessions.append({
                "id": session.session_id,
                "status": session.status,
                "initiator": session.initiator_hospital,
                "resource_type": session.request.resource_type,
                "created_at": session.created_at.isoformat()
            })
        
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/trigger-surge")
async def trigger_demo_surge(app_request: Request):
    """
    Demo endpoint: Trigger a simulated disease outbreak
    This will automatically start a negotiation
    """
    
    try:
        multi_agent_service = app_request.app.state.multi_agent_service
        
        # Simulate surge detection
        surge_event = {
            "event_type": "respiratory_outbreak",
            "predicted_cases": 180,
            "timeframe": "Nov 12-14, 2024",
            "required_resources": {
                "ventilators": 8,
                "pulmonologists": 2,
                "icu_beds": 15
            }
        }
        
        # Auto-trigger negotiation
        negotiation_id = "demo_surge_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            "success": True,
            "surge_detected": surge_event,
            "action": "auto_negotiation_triggered",
            "negotiation_id": negotiation_id,
            "message": "AI agents are now negotiating resource sharing autonomously"
        }
        
    except Exception as e:
        logger.error(f"Demo surge trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))