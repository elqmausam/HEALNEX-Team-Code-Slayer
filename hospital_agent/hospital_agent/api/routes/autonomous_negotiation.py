# hospital_agent/api/routes/autonomous_negotiation.py
"""
Autonomous Negotiation Routes - Simple test endpoint
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class NegotiationScenario(BaseModel):
    """Negotiation scenario request"""
    initiator_hospital_id: Optional[str] = "HOSP_A"
    resource_type: Optional[str] = "ventilators"
    quantity: Optional[int] = 5
    urgency: Optional[str] = "high"
    duration_days: Optional[int] = 7
    max_budget: Optional[float] = 500000


@router.post("/run-fake-scenario")
async def run_fake_scenario(
    scenario: Optional[NegotiationScenario] = None,
    request: Request = None
):
    """
    Run a fake negotiation scenario for testing
    """
    try:
        # Get the multi-agent service
        if not hasattr(request.app.state, 'multi_agent_service'):
            raise HTTPException(
                status_code=503, 
                detail="Multi-agent service not initialized. Make sure OPENAI_API_KEY is set."
            )
        
        multi_agent_service = request.app.state.multi_agent_service
        
        # Use default scenario if none provided
        if scenario is None:
            scenario = NegotiationScenario()
        
        # Start the negotiation and stream results
        async def event_generator():
            try:
                async for event in multi_agent_service.initiate_negotiation(
                    initiator_hospital_id=scenario.initiator_hospital_id,
                    resource_type=scenario.resource_type,
                    quantity=scenario.quantity,
                    urgency=scenario.urgency,
                    duration_days=scenario.duration_days,
                    max_budget=scenario.max_budget
                ):
                    yield f"data: {json.dumps(event)}\n\n"
                
                # Send completion
                yield f"data: {json.dumps({'event': 'stream_complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in negotiation stream: {e}", exc_info=True)
                error_event = {
                    "event": "error",
                    "message": str(e),
                    "type": type(e).__name__
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start negotiation scenario: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start negotiation: {str(e)}"
        )


@router.get("/status")
async def get_negotiation_status(request: Request):
    """
    Get status of autonomous negotiation system
    """
    try:
        if not hasattr(request.app.state, 'multi_agent_service'):
            return {
                "status": "unavailable",
                "message": "Multi-agent service not initialized"
            }
        
        multi_agent_service = request.app.state.multi_agent_service
        
        return {
            "status": "online",
            "total_agents": len(multi_agent_service.agents),
            "active_sessions": len(multi_agent_service.sessions),
            "agents": list(multi_agent_service.agents.keys())
        }
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-simple")
async def test_simple(request: Request):
    """
    Simple test endpoint without streaming
    """
    try:
        if not hasattr(request.app.state, 'multi_agent_service'):
            return {
                "success": False,
                "error": "Multi-agent service not initialized",
                "hint": "Check OPENAI_API_KEY environment variable"
            }
        
        multi_agent_service = request.app.state.multi_agent_service
        agents = multi_agent_service.get_all_agents()
        
        return {
            "success": True,
            "message": "Multi-agent service is working",
            "agent_count": len(agents),
            "agents": list(agents.keys())
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }