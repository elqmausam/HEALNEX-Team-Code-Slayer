

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
import uuid

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def datetime_serializer(obj):
    """JSON serializer for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def dataclass_to_dict(obj):
    """Convert dataclass to dict with datetime serialization"""
    result = {}
    for key, value in asdict(obj).items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = {k: v.isoformat() if isinstance(v, datetime) else v 
                          for k, v in value.items()}
        elif isinstance(value, list):
            result[key] = [item.isoformat() if isinstance(item, datetime) else item 
                          for item in value]
        else:
            result[key] = value
    return result


@dataclass
class ResourceRequest:
    """Resource request from a hospital"""
    request_id: str
    hospital_id: str
    hospital_name: str
    resource_type: str  # "ventilators", "beds", "staff", "medicine"
    quantity: int
    urgency: str  # "critical", "high", "medium", "low"
    needed_from: datetime
    needed_until: datetime
    max_price: float
    additional_details: Dict
    
    
@dataclass
class ResourceOffer:
    """Resource offer from a hospital"""
    offer_id: str
    hospital_id: str
    hospital_name: str
    resource_type: str
    quantity: int
    price_per_unit: float
    available_from: datetime
    available_until: datetime
    conditions: List[str]
    

@dataclass
class NegotiationSession:
    """A negotiation session between hospitals"""
    session_id: str
    initiator_hospital: str
    participant_hospitals: List[str]
    request: ResourceRequest
    offers: List[ResourceOffer]
    status: str  # "initiated", "negotiating", "completed", "failed"
    messages: List[Dict]
    created_at: datetime
    updated_at: datetime
    final_agreement: Optional[Dict] = None


class HospitalAgent:
    """Individual hospital agent with AI decision making"""
    
    def __init__(self, hospital_id: str, hospital_name: str, hospital_data: Dict, openai_api_key: str):
        self.hospital_id = hospital_id
        self.hospital_name = hospital_name
        self.hospital_data = hospital_data
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.personality = self._generate_personality()
        
    def _generate_personality(self) -> str:
        """Generate agent personality based on hospital characteristics"""
        if "teaching" in self.hospital_name.lower():
            return "academic_collaborative"
        elif "private" in self.hospital_data.get("type", "").lower():
            return "business_oriented"
        else:
            return "community_focused"
    
    def _supports_json_mode(self, model: str) -> bool:
        """Check if model supports JSON mode"""
        json_mode_models = [
            "gpt-4-turbo", "gpt-4-turbo-preview", 
            "gpt-4-1106-preview", "gpt-4-0125-preview",
            "gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125"
        ]
        return any(supported in model for supported in json_mode_models)
    
    def _extract_json(self, content: str) -> str:
        """Extract JSON from content that might be wrapped in markdown"""
        content = content.strip()
        
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return content
    
    async def analyze_request(self, request: ResourceRequest) -> Dict:
        """Analyze incoming resource request using AI"""
        
        prompt = f"""You are the AI agent for {self.hospital_name}, a {self.hospital_data.get('type', 'hospital')}.

INCOMING REQUEST:
- From: {request.hospital_name}
- Resource: {request.resource_type}
- Quantity: {request.quantity}
- Urgency: {request.urgency}
- Duration: {request.needed_from.strftime('%Y-%m-%d')} to {request.needed_until.strftime('%Y-%m-%d')}
- Max Budget: ₹{request.max_price:,.0f}

YOUR HOSPITAL INVENTORY:
{json.dumps(self.hospital_data.get('resources', {}), indent=2)}

YOUR HOSPITAL STATUS:
- Current occupancy: {self.hospital_data.get('occupancy', 0)}%
- Available staff: {self.hospital_data.get('available_staff', 0)}
- Financial health: {self.hospital_data.get('financial_health', 'stable')}

Analyze this request and respond ONLY with valid JSON in this exact format:
{{
    "can_help": true/false,
    "quantity_available": number,
    "proposed_price_per_unit": number,
    "conditions": ["list", "of", "conditions"],
    "reasoning": "brief explanation",
    "confidence": 0-100
}}

Be realistic, consider your hospital's needs, and aim for mutually beneficial arrangements."""

        try:
            model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            
            # Build request parameters
            request_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an intelligent hospital resource management agent. Make data-driven decisions that balance helping other hospitals with maintaining your own operations. ALWAYS respond with valid JSON only, no markdown, no explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            # Add JSON mode if supported
            if self._supports_json_mode(model):
                request_params["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            # Extract and parse JSON
            json_content = self._extract_json(content)
            return json.loads(json_content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Agent {self.hospital_id} JSON parse error: {e}")
            logger.error(f"Content was: {content[:200]}")
            return {
                "can_help": False,
                "reasoning": "Invalid response format",
                "confidence": 0
            }
        except Exception as e:
            logger.error(f"Agent {self.hospital_id} analysis failed: {e}", exc_info=True)
            return {
                "can_help": False,
                "reasoning": f"System error: {str(e)}",
                "confidence": 0
            }
    
    async def negotiate_offer(self, request: ResourceRequest, competing_offers: List[ResourceOffer]) -> Dict:
        """Negotiate and potentially adjust offer based on competition"""
        
        prompt = f"""You are negotiating on behalf of {self.hospital_name}.

ORIGINAL REQUEST:
- Resource: {request.resource_type}
- Quantity: {request.quantity}
- Budget: ₹{request.max_price:,.0f}

COMPETING OFFERS:
{json.dumps([{
    'hospital': o.hospital_name,
    'quantity': o.quantity,
    'price': o.price_per_unit,
    'conditions': o.conditions
} for o in competing_offers], indent=2)}

Should you adjust your offer to be more competitive? Respond ONLY with valid JSON:
{{
    "adjust_offer": true/false,
    "new_price_per_unit": number (if adjusting),
    "new_conditions": ["list"] (if adjusting),
    "strategy": "explanation of your strategy"
}}"""

        try:
            model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            
            request_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a strategic negotiator for a hospital. Balance competitiveness with profitability. ALWAYS respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }
            
            if self._supports_json_mode(model):
                request_params["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            json_content = self._extract_json(content)
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"Negotiation error: {e}", exc_info=True)
            return {"adjust_offer": False}


class MultiAgentCoordinationService:
    """The Parliament - Multi-agent coordination system"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.agents: Dict[str, HospitalAgent] = {}
        self.sessions: Dict[str, NegotiationSession] = {}
        self.client = AsyncOpenAI(api_key=openai_api_key)
        
        # Initialize demo hospitals
        self._initialize_demo_hospitals()
    
    def _initialize_demo_hospitals(self):
        """Initialize demo hospital agents with fake but realistic data"""
        
        demo_hospitals = [
            {
                "id": "HOSP_A",
                "name": "Apollo City Hospital",
                "type": "Private Multi-specialty",
                "resources": {
                    "ventilators": {"total": 20, "available": 12},
                    "icu_beds": {"total": 50, "available": 18},
                    "pulmonologists": {"total": 5, "available": 2},
                    "nurses": {"total": 150, "available": 30}
                },
                "occupancy": 75,
                "available_staff": 45,
                "financial_health": "excellent",
                "location": {"lat": 28.6139, "lon": 77.2090}
            },
            {
                "id": "HOSP_B",
                "name": "Max Super Specialty Hospital",
                "type": "Private Tertiary Care",
                "resources": {
                    "ventilators": {"total": 15, "available": 8},
                    "icu_beds": {"total": 40, "available": 15},
                    "pulmonologists": {"total": 4, "available": 1},
                    "nurses": {"total": 120, "available": 25}
                },
                "occupancy": 82,
                "available_staff": 38,
                "financial_health": "good",
                "location": {"lat": 28.5494, "lon": 77.2495}
            },
            {
                "id": "HOSP_C",
                "name": "Fortis Medical Centre",
                "type": "Private Teaching Hospital",
                "resources": {
                    "ventilators": {"total": 25, "available": 15},
                    "icu_beds": {"total": 60, "available": 25},
                    "pulmonologists": {"total": 6, "available": 3},
                    "nurses": {"total": 180, "available": 40}
                },
                "occupancy": 68,
                "available_staff": 52,
                "financial_health": "excellent",
                "location": {"lat": 28.4595, "lon": 77.0266}
            }
        ]
        
        for hospital in demo_hospitals:
            agent = HospitalAgent(
                hospital_id=hospital["id"],
                hospital_name=hospital["name"],
                hospital_data=hospital,
                openai_api_key=self.openai_api_key
            )
            self.agents[hospital["id"]] = agent
            logger.info(f"Initialized agent for {hospital['name']}")
    
    def _supports_json_mode(self, model: str) -> bool:
        """Check if model supports JSON mode"""
        json_mode_models = [
            "gpt-4-turbo", "gpt-4-turbo-preview", 
            "gpt-4-1106-preview", "gpt-4-0125-preview",
            "gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125"
        ]
        return any(supported in model for supported in json_mode_models)
    
    def _extract_json(self, content: str) -> str:
        """Extract JSON from content that might be wrapped in markdown"""
        content = content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return content
    
    async def initiate_negotiation(
        self,
        initiator_hospital_id: str,
        resource_type: str,
        quantity: int,
        urgency: str,
        duration_days: int,
        max_budget: float,
        additional_details: Optional[Dict] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Initiate autonomous negotiation session
        Yields real-time updates as negotiation progresses
        """
        
        session_id = str(uuid.uuid4())
        
        # Create request
        request = ResourceRequest(
            request_id=str(uuid.uuid4()),
            hospital_id=initiator_hospital_id,
            hospital_name=self.agents[initiator_hospital_id].hospital_name,
            resource_type=resource_type,
            quantity=quantity,
            urgency=urgency,
            needed_from=datetime.now() + timedelta(days=1),
            needed_until=datetime.now() + timedelta(days=duration_days),
            max_price=max_budget,
            additional_details=additional_details or {}
        )
        
        # Get other hospital agents
        participant_ids = [hid for hid in self.agents.keys() if hid != initiator_hospital_id]
        
        # Create session
        session = NegotiationSession(
            session_id=session_id,
            initiator_hospital=initiator_hospital_id,
            participant_hospitals=participant_ids,
            request=request,
            offers=[],
            status="initiated",
            messages=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.sessions[session_id] = session
        
        # Yield initiation event
        yield {
            "event": "negotiation_initiated",
            "session_id": session_id,
            "request": dataclass_to_dict(request),
            "timestamp": datetime.now().isoformat()
        }
        
        # Phase 1: Broadcast request to all agents
        session.status = "broadcasting"
        yield {
            "event": "broadcasting_request",
            "participants": [self.agents[hid].hospital_name for hid in participant_ids],
            "timestamp": datetime.now().isoformat()
        }
        
        await asyncio.sleep(1)  # Simulate network delay
        
        # Phase 2: Collect initial responses
        session.status = "collecting_responses"
        
        for hospital_id in participant_ids:
            agent = self.agents[hospital_id]
            
            yield {
                "event": "agent_analyzing",
                "agent": agent.hospital_name,
                "timestamp": datetime.now().isoformat()
            }
            
            analysis = await agent.analyze_request(request)
            
            session.messages.append({
                "from": hospital_id,
                "type": "analysis",
                "content": analysis,
                "timestamp": datetime.now().isoformat()
            })
            
            if analysis.get("can_help"):
                offer = ResourceOffer(
                    offer_id=str(uuid.uuid4()),
                    hospital_id=hospital_id,
                    hospital_name=agent.hospital_name,
                    resource_type=resource_type,
                    quantity=analysis["quantity_available"],
                    price_per_unit=analysis["proposed_price_per_unit"],
                    available_from=request.needed_from,
                    available_until=request.needed_until,
                    conditions=analysis.get("conditions", [])
                )
                session.offers.append(offer)
                
                yield {
                    "event": "offer_received",
                    "agent": agent.hospital_name,
                    "offer": dataclass_to_dict(offer),
                    "reasoning": analysis.get("reasoning"),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                yield {
                    "event": "offer_declined",
                    "agent": agent.hospital_name,
                    "reason": analysis.get("reasoning"),
                    "timestamp": datetime.now().isoformat()
                }
        
        # Phase 3: Negotiation round (if multiple offers)
        if len(session.offers) > 1:
            session.status = "negotiating"
            
            yield {
                "event": "negotiation_round_started",
                "offers_count": len(session.offers),
                "timestamp": datetime.now().isoformat()
            }
            
            for offer in session.offers:
                agent = self.agents[offer.hospital_id]
                negotiation_result = await agent.negotiate_offer(request, session.offers)
                
                if negotiation_result.get("adjust_offer"):
                    yield {
                        "event": "offer_adjusted",
                        "agent": agent.hospital_name,
                        "adjustment": negotiation_result,
                        "timestamp": datetime.now().isoformat()
                    }
        
        # Phase 4: Decision making
        session.status = "deciding"
        
        yield {
            "event": "making_decision",
            "timestamp": datetime.now().isoformat()
        }
        
        decision = await self._make_decision(session)
        
        session.final_agreement = decision
        session.status = "completed"
        
        yield {
            "event": "negotiation_completed",
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _make_decision(self, session: NegotiationSession) -> Dict:
        """Use AI to make final decision on best offer"""
        
        if not session.offers:
            return {
                "success": False,
                "reason": "No offers received",
                "recommendations": ["Try increasing budget", "Reduce quantity", "Extend timeline"]
            }
        
        prompt = f"""You are making a decision for {session.request.hospital_name}.

REQUEST:
- Resource: {session.request.resource_type}
- Quantity needed: {session.request.quantity}
- Max budget: ₹{session.request.max_price:,.0f}
- Urgency: {session.request.urgency}

OFFERS RECEIVED:
{json.dumps([{
    'hospital': o.hospital_name,
    'quantity': o.quantity,
    'price_per_unit': o.price_per_unit,
    'total_cost': o.quantity * o.price_per_unit,
    'conditions': o.conditions
} for o in session.offers], indent=2)}

Select the best offer(s) considering cost, reliability, and conditions. You may select multiple offers if needed to meet quantity. Respond ONLY with valid JSON:
{{
    "success": true/false,
    "selected_offers": [
        {{
            "hospital": "name",
            "quantity": number,
            "total_cost": number,
            "reason": "why selected"
        }}
    ],
    "total_cost": number,
    "reasoning": "detailed explanation"
}}"""

        try:
            model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            
            request_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert procurement decision maker for hospitals. Optimize for cost, reliability, and speed. ALWAYS respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5
            }
            
            if self._supports_json_mode(model):
                request_params["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            json_content = self._extract_json(content)
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"Decision making failed: {e}", exc_info=True)
            return {
                "success": False,
                "reason": "System error during decision making"
            }
    
    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get negotiation session by ID"""
        return self.sessions.get(session_id)
    
    def get_all_agents(self) -> Dict[str, Dict]:
        """Get all hospital agents info"""
        return {
            agent_id: {
                "id": agent.hospital_id,
                "name": agent.hospital_name,
                "data": agent.hospital_data
            }
            for agent_id, agent in self.agents.items()
        }