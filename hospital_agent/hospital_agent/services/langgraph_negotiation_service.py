
import os
import json
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated, TYPE_CHECKING
from datetime import datetime, timedelta
import asyncio
import random



# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    StateGraph = None
    HumanMessage = None
    AIMessage = None
    ChatGoogleGenerativeAI = None

if TYPE_CHECKING:
    # Only for typing; does NOT execute at runtime
    from langgraph.graph import StateGraph as _StateGraph
else:
    _StateGraph = Any

logger = logging.getLogger(__name__)


# ============================================
# State Definition for LangGraph
# ============================================

class NegotiationState(TypedDict):
    """State object for the negotiation workflow"""
    
    # Request details
    requesting_hospital: str
    resource_type: str
    quantity: int
    urgency: str  # low, medium, high, critical
    max_budget: Optional[float]
    delivery_deadline: Optional[str]
    
    # Workflow state
    current_step: str
    analysis_complete: bool
    offers_collected: bool
    negotiation_complete: bool
    contract_finalized: bool
    
    # Data collected during workflow
    need_analysis: Optional[Dict[str, Any]]
    broadcast_sent: bool
    offers: List[Dict[str, Any]]
    offer_evaluations: Optional[Dict[str, Any]]
    negotiation_rounds: List[Dict[str, Any]]
    best_offer: Optional[Dict[str, Any]]
    final_contract: Optional[Dict[str, Any]]
    
    # Notifications
    notifications: List[Dict[str, Any]]
    
    # Metadata
    started_at: str
    completed_at: Optional[str]
    total_time_seconds: Optional[float]


# ============================================
# LangGraph Negotiation Service
# ============================================

class LangGraphNegotiationService:
    """
    Autonomous negotiation agent using LangGraph
    
    Workflow:
    1. Analyze Need (LLM)
    2. Broadcast Request
    3. Collect Offers
    4. Evaluate Offers (LLM)
    5. Negotiate (LLM, multi-round)
    6. Finalize Contract
    7. Notify (RING! 🔔)
    """
    
    def __init__(self, cache_service=None):
        self.cache_service = cache_service
        
        # Initialize LLM
        if ChatGoogleGenerativeAI:
            self.llm = ChatGoogleGenerativeAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
                google_api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.7
            )
        else:
            self.llm = None
            logger.warning("⚠️  LangChain not installed. LangGraph features disabled.")
        
        # Build workflow graph
        self.workflow: Optional[_StateGraph] = self._build_workflow()
        self.initialized = False
    
    async def initialize(self):
        """Initialize service"""
        if StateGraph and self.llm:
            self.initialized = True
            logger.info("✅ LangGraph Negotiation Service initialized")
        else:
            logger.warning("⚠️  LangGraph not available. Install: pip install langgraph langchain langchain-google-genai")
    
    def _build_workflow(self) -> Optional[_StateGraph]:
        """Build the LangGraph workflow"""
        
        if not StateGraph:
            return None
        
        # Create workflow graph
        workflow = StateGraph(NegotiationState)
        
        # Add nodes
        workflow.add_node("analyze_need", self._analyze_need)
        workflow.add_node("broadcast_request", self._broadcast_request)
        workflow.add_node("collect_offers", self._collect_offers)
        workflow.add_node("evaluate_offers", self._evaluate_offers)
        workflow.add_node("negotiate", self._negotiate)
        workflow.add_node("finalize_contract", self._finalize_contract)
        workflow.add_node("notify", self._notify)
        
        # Define edges
        workflow.set_entry_point("analyze_need")
        workflow.add_edge("analyze_need", "broadcast_request")
        workflow.add_edge("broadcast_request", "collect_offers")
        workflow.add_edge("collect_offers", "evaluate_offers")
        workflow.add_edge("evaluate_offers", "negotiate")
        workflow.add_edge("negotiate", "finalize_contract")
        workflow.add_edge("finalize_contract", "notify")
        workflow.add_edge("notify", END)
        
        return workflow.compile()
    
    # ============================================
    # Workflow Nodes
    # ============================================
    
    async def _analyze_need(self, state: NegotiationState) -> NegotiationState:
        """
        Node 1: Analyze the resource need using LLM
        Creates negotiation strategy
        """
        logger.info(f"📊 Analyzing need for {state['quantity']} {state['resource_type']}")
        
        if not self.llm:
            # Fallback without LLM
            state["need_analysis"] = {
                "priority": "high",
                "strategy": "competitive",
                "max_acceptable_price": 10000,
                "reasoning": "Automated analysis"
            }
            state["analysis_complete"] = True
            return state
        
        # Use LLM to analyze
        prompt = f"""Analyze this hospital resource request and create a negotiation strategy:

Resource: {state['resource_type']}
Quantity: {state['quantity']}
Urgency: {state['urgency']}
Max Budget: ₹{state.get('max_budget', 'Not specified')}
Deadline: {state.get('delivery_deadline', 'ASAP')}

Provide analysis in JSON format:
{{
  "priority": "low|medium|high|critical",
  "strategy": "aggressive|competitive|cooperative|flexible",
  "max_acceptable_price_per_unit": <number>,
  "negotiation_approach": "brief description",
  "key_requirements": ["requirement1", "requirement2"],
  "fallback_options": ["option1", "option2"]
}}"""
        
        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=prompt)]
            )
            
            # Parse response
            analysis_text = response.content
            
            # Extract JSON
            if "```json" in analysis_text:
                analysis_text = analysis_text.split("```json")[1].split("```")[0]
            elif "```" in analysis_text:
                analysis_text = analysis_text.split("```")[1].split("```")[0]
            
            analysis = json.loads(analysis_text.strip())
            
            state["need_analysis"] = analysis
            state["analysis_complete"] = True
            state["current_step"] = "analyze_need"
            
            logger.info(f"✅ Need analysis complete: {analysis['strategy']} strategy")
        
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}, using fallback")
            state["need_analysis"] = {
                "priority": "high",
                "strategy": "competitive",
                "max_acceptable_price_per_unit": 10000,
                "negotiation_approach": "Standard negotiation",
                "key_requirements": ["Quality", "Timely delivery"],
                "fallback_options": ["Alternative suppliers"]
            }
            state["analysis_complete"] = True
        
        return state
    
    async def _broadcast_request(self, state: NegotiationState) -> NegotiationState:
        """
        Node 2: Broadcast resource request to hospital network
        """
        logger.info(f"📢 Broadcasting request to hospital network")
        
        # Simulate broadcasting to hospital network
        # In production, this would call a real hospital network API
        
        broadcast_data = {
            "requesting_hospital": state["requesting_hospital"],
            "resource_type": state["resource_type"],
            "quantity": state["quantity"],
            "urgency": state["urgency"],
            "delivery_deadline": state.get("delivery_deadline"),
            "broadcast_time": datetime.now().isoformat(),
            "response_deadline": (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        
        # Store broadcast in cache for other hospitals to see
        if self.cache_service:
            await self.cache_service.set(
                f"broadcast:{state['requesting_hospital']}",
                broadcast_data,
                ttl=1800  # 30 minutes
            )
        
        state["broadcast_sent"] = True
        state["current_step"] = "broadcast_request"
        
        logger.info(f"✅ Broadcast sent at {broadcast_data['broadcast_time']}")
        
        return state
    
    async def _collect_offers(self, state: NegotiationState) -> NegotiationState:
        """
        Node 3: Collect offers from responding hospitals
        Waits for responses or timeout
        """
        logger.info(f"📥 Collecting offers from hospitals...")
        
        # In production, this would poll for real offers
        # For now, simulate waiting and collecting
        
        # Simulate 2-minute collection period
        collection_time = 2  # seconds in demo, minutes in production
        await asyncio.sleep(collection_time)
        
        # Get offers from cache (or generate fake ones for demo)
        offers = []
        
        if self.cache_service:
            # Try to get real offers
            offer_keys = await self.cache_service.get_keys(
                f"offer:{state['requesting_hospital']}:*"
            )
            
            for key in offer_keys:
                offer = await self.cache_service.get(key)
                if offer:
                    offers.append(offer)
        
        # If no offers, this will be empty (handled in evaluate_offers)
        state["offers"] = offers
        state["offers_collected"] = True
        state["current_step"] = "collect_offers"
        
        logger.info(f"✅ Collected {len(offers)} offers")
        
        return state
    
    async def _evaluate_offers(self, state: NegotiationState) -> NegotiationState:
        """
        Node 4: Evaluate and rank offers using LLM
        """
        logger.info(f"⚖️  Evaluating {len(state['offers'])} offers")
        
        if not state["offers"]:
            logger.warning("⚠️  No offers received")
            state["offer_evaluations"] = {
                "ranked_offers": [],
                "recommendation": "No offers received. Consider expanding search or adjusting requirements."
            }
            state["current_step"] = "evaluate_offers"
            return state
        
        if not self.llm:
            # Simple ranking without LLM
            sorted_offers = sorted(
                state["offers"],
                key=lambda x: x.get("total_price", float('inf'))
            )
            
            state["offer_evaluations"] = {
                "ranked_offers": sorted_offers,
                "top_choice": sorted_offers[0] if sorted_offers else None
            }
            state["current_step"] = "evaluate_offers"
            return state
        
        # Use LLM to evaluate
        prompt = f"""Evaluate these hospital resource offers:

Request: {state['quantity']} {state['resource_type']}
Urgency: {state['urgency']}
Strategy: {state['need_analysis']['strategy']}

Offers:
{json.dumps(state['offers'], indent=2)}

Rank the offers and provide evaluation in JSON format:
{{
  "ranked_offers": [
    {{
      "hospital_id": "...",
      "rank": 1,
      "score": 0-100,
      "pros": ["..."],
      "cons": ["..."],
      "negotiation_potential": "low|medium|high"
    }}
  ],
  "recommendation": "Which offer to negotiate with and why",
  "negotiation_strategy": "Specific strategy for top choice"
}}"""
        
        try:
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=prompt)]
            )
            
            evaluation_text = response.content
            
            # Extract JSON
            if "```json" in evaluation_text:
                evaluation_text = evaluation_text.split("```json")[1].split("```")[0]
            
            evaluation = json.loads(evaluation_text.strip())
            
            state["offer_evaluations"] = evaluation
            state["current_step"] = "evaluate_offers"
            
            logger.info(f"✅ Offers evaluated, top choice: {evaluation['ranked_offers'][0]['hospital_id']}")
        
        except Exception as e:
            logger.error(f"Offer evaluation failed: {e}")
            # Fallback: rank by price
            sorted_offers = sorted(state["offers"], key=lambda x: x.get("total_price", float('inf')))
            state["offer_evaluations"] = {
                "ranked_offers": sorted_offers,
                "recommendation": "Ranked by price (LLM evaluation failed)"
            }
        
        return state
    
    async def _negotiate(self, state: NegotiationState) -> NegotiationState:
        """
        Node 5: Conduct multi-round negotiation with top choice
        """
        logger.info(f"🤝 Starting negotiation...")
        
        evaluations = state["offer_evaluations"]
        
        if not evaluations.get("ranked_offers"):
            logger.warning("⚠️  No offers to negotiate")
            state["negotiation_complete"] = True
            state["best_offer"] = None
            return state
        
        top_offer = evaluations["ranked_offers"][0]
        
        # Simulate 2-3 rounds of negotiation
        rounds = []
        current_price = top_offer.get("total_price", 0)
        target_price = state["need_analysis"].get("max_acceptable_price_per_unit", 0) * state["quantity"]
        
        for round_num in range(1, 4):
            logger.info(f"  Round {round_num}: Current price ₹{current_price}")
            
            if not self.llm:
                # Simple negotiation without LLM
                reduction = current_price * 0.05  # 5% reduction per round
                new_price = max(current_price - reduction, target_price)
                
                round_data = {
                    "round": round_num,
                    "our_offer": new_price,
                    "their_response": new_price,
                    "accepted": round_num == 3 or new_price <= target_price
                }
            else:
                # Use LLM for negotiation
                prompt = f"""You are negotiating for {state['quantity']} {state['resource_type']}.

Current offer: ₹{current_price}
Target price: ₹{target_price}
Strategy: {state['need_analysis']['strategy']}
Round: {round_num}/3

Provide your negotiation move in JSON:
{{
  "counter_offer": <number>,
  "reasoning": "Why this offer",
  "concession_justification": "What you're offering in return",
  "expected_response": "likely|neutral|unlikely"
}}"""
                
                try:
                    response = await asyncio.to_thread(
                        self.llm.invoke,
                        [HumanMessage(content=prompt)]
                    )
                    
                    negotiation_text = response.content
                    if "```json" in negotiation_text:
                        negotiation_text = negotiation_text.split("```json")[1].split("```")[0]
                    
                    negotiation_move = json.loads(negotiation_text.strip())
                    
                    new_price = negotiation_move["counter_offer"]
                    
                    # Simulate other hospital's response
                    # In production, this would be a real API call
                    if new_price >= target_price * 0.95:  # Within 5% of target
                        accepted = True
                    else:
                        accepted = round_num == 3  # Accept on final round
                    
                    round_data = {
                        "round": round_num,
                        "our_offer": new_price,
                        "reasoning": negotiation_move["reasoning"],
                        "their_response": new_price if accepted else current_price * 0.98,
                        "accepted": accepted
                    }
                
                except Exception as e:
                    logger.error(f"LLM negotiation failed: {e}")
                    new_price = current_price * 0.95
                    round_data = {
                        "round": round_num,
                        "our_offer": new_price,
                        "accepted": round_num == 3
                    }
            
            rounds.append(round_data)
            current_price = round_data["their_response"]
            
            if round_data["accepted"]:
                logger.info(f"  ✅ Offer accepted at ₹{current_price}")
                break
            
            await asyncio.sleep(0.5)  # Simulate negotiation time
        
        # Final offer
        final_offer = {
            **top_offer,
            "negotiated_price": current_price,
            "original_price": top_offer.get("total_price"),
            "savings": top_offer.get("total_price", 0) - current_price,
            "negotiation_rounds": len(rounds)
        }
        
        state["negotiation_rounds"] = rounds
        state["best_offer"] = final_offer
        state["negotiation_complete"] = True
        state["current_step"] = "negotiate"
        
        logger.info(f"✅ Negotiation complete: ₹{current_price} (saved ₹{final_offer['savings']})")
        
        return state
    
    async def _finalize_contract(self, state: NegotiationState) -> NegotiationState:
        """
        Node 6: Generate final contract
        """
        logger.info(f"📜 Finalizing contract...")
        
        if not state.get("best_offer"):
            logger.warning("⚠️  No offer to finalize")
            state["contract_finalized"] = False
            return state
        
        best_offer = state["best_offer"]
        
        # Generate contract
        contract = {
            "contract_id": f"contract-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
            "requesting_hospital": state["requesting_hospital"],
            "supplying_hospital": best_offer.get("hospital_id"),
            "resource_type": state["resource_type"],
            "quantity": state["quantity"],
            "unit_price": best_offer["negotiated_price"] / state["quantity"],
            "total_price": best_offer["negotiated_price"],
            "delivery_deadline": state.get("delivery_deadline", "ASAP"),
            "quality_standards": best_offer.get("quality_certification", "Standard"),
            "payment_terms": "Net 30 days",
            "created_at": datetime.now().isoformat(),
            "status": "pending_signature",
            "negotiation_summary": {
                "original_price": best_offer["original_price"],
                "final_price": best_offer["negotiated_price"],
                "savings": best_offer["savings"],
                "rounds": best_offer["negotiation_rounds"]
            }
        }
        
        # Store contract
        if self.cache_service:
            await self.cache_service.set(
                f"contract:{contract['contract_id']}",
                contract,
                ttl=604800  # 7 days
            )
        
        state["final_contract"] = contract
        state["contract_finalized"] = True
        state["current_step"] = "finalize_contract"
        
        logger.info(f"✅ Contract finalized: {contract['contract_id']}")
        
        return state
    
    async def _notify(self, state: NegotiationState) -> NegotiationState:
        """
        Node 7: Send notifications (RING! 🔔)
        """
        logger.info(f"🔔 RING! Sending notifications...")
        
        # Create notification
        if state.get("final_contract"):
            contract = state["final_contract"]
            
            notification = {
                "type": "success",
                "title": "Negotiation Complete! 🎉",
                "message": f"Successfully negotiated {state['quantity']} {state['resource_type']} for ₹{contract['total_price']:,.2f}",
                "contract_id": contract["contract_id"],
                "details": {
                    "supplier": contract["supplying_hospital"],
                    "total_cost": contract["total_price"],
                    "savings": contract["negotiation_summary"]["savings"],
                    "delivery": contract["delivery_deadline"]
                },
                "timestamp": datetime.now().isoformat(),
                "action_required": "Review and sign contract"
            }
        else:
            notification = {
                "type": "error",
                "title": "Negotiation Failed",
                "message": "Unable to secure resources. No suitable offers received.",
                "timestamp": datetime.now().isoformat(),
                "action_required": "Review requirements and try again"
            }
        
        # Store notification
        if self.cache_service:
            await self.cache_service.set(
                f"notification:{state['requesting_hospital']}",
                notification,
                ttl=86400  # 24 hours
            )
        
        state["notifications"].append(notification)
        state["completed_at"] = datetime.now().isoformat()
        
        # Calculate total time
        started = datetime.fromisoformat(state["started_at"])
        completed = datetime.fromisoformat(state["completed_at"])
        state["total_time_seconds"] = (completed - started).total_seconds()
        
        logger.info(f"🔔 RING! RING! Notification sent: {notification['title']}")
        logger.info(f"✅ Workflow complete in {state['total_time_seconds']:.1f} seconds")
        
        return state
    
    # ============================================
    # Public Methods
    # ============================================
    
    async def run_autonomous_negotiation(
        self,
        requesting_hospital: str,
        resource_type: str,
        quantity: int,
        urgency: str = "medium",
        max_budget: Optional[float] = None,
        delivery_deadline: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete autonomous negotiation workflow
        """
        
        if not self.workflow:
            raise Exception("LangGraph not available. Install required packages.")
        
        logger.info(f"🚀 Starting autonomous negotiation for {requesting_hospital}")
        
        # Initialize state
        initial_state = NegotiationState(
            requesting_hospital=requesting_hospital,
            resource_type=resource_type,
            quantity=quantity,
            urgency=urgency,
            max_budget=max_budget,
            delivery_deadline=delivery_deadline,
            current_step="initializing",
            analysis_complete=False,
            offers_collected=False,
            negotiation_complete=False,
            contract_finalized=False,
            need_analysis=None,
            broadcast_sent=False,
            offers=[],
            offer_evaluations=None,
            negotiation_rounds=[],
            best_offer=None,
            final_contract=None,
            notifications=[],
            started_at=datetime.now().isoformat(),
            completed_at=None,
            total_time_seconds=None
        )
        
        # Run workflow
        try:
            final_state = await asyncio.to_thread(
                self.workflow.invoke,
                initial_state
            )
            
            return {
                "status": "success",
                "workflow_complete": True,
                "final_state": final_state,
                "contract": final_state.get("final_contract"),
                "notifications": final_state.get("notifications"),
                "total_time_seconds": final_state.get("total_time_seconds")
            }
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise
    
    def get_workflow_graph(self) -> str:
        """
        Get Mermaid diagram of the workflow
        """
        return """
graph TD
    A[Start] --> B[Analyze Need]
    B --> C[Broadcast Request]
    C --> D[Collect Offers]
    D --> E[Evaluate Offers]
    E --> F[Negotiate]
    F --> G[Finalize Contract]
    G --> H[Notify 🔔]
    H --> I[End]
    
    style A fill:#90EE90
    style I fill:#FFB6C1
    style H fill:#FFD700
    style F fill:#87CEEB
"""