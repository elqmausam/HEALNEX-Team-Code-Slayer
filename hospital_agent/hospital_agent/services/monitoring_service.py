

from datetime import datetime
from typing import Dict, Any
import time
import logging

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring application metrics"""
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "avg_response_time": 0.0,
            "predictions_generated": 0,
            "embeddings_created": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.start_time = time.time()
    
    def get_timestamp(self) -> str:
        """Get current ISO timestamp"""
        return datetime.utcnow().isoformat() + "Z"
    
    def record_request(self, success: bool, response_time: float):
        """Record API request metrics"""
        self.metrics["requests_total"] += 1
        
        if success:
            self.metrics["requests_success"] += 1
        else:
            self.metrics["requests_error"] += 1
        
        # Update average response time
        total = self.metrics["requests_total"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )
    
    def record_prediction(self):
        """Record prediction generation"""
        self.metrics["predictions_generated"] += 1
    
    def record_embedding(self):
        """Record embedding creation"""
        self.metrics["embeddings_created"] += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics["cache_misses"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        uptime = time.time() - self.start_time
        
        return {
            **self.metrics,
            "uptime_seconds": uptime,
            "cache_hit_rate": (
                self.metrics["cache_hits"] / 
                (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0
                else 0
            )
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {k: 0 for k in self.metrics}
        self.start_time = time.time()


# hospital_agent/services/__init__.py
from .llm_service import LLMService
from .vector_service import VectorService
from .prediction_service import PredictionService
from .cache_service import CacheService
from .monitoring_service import MonitoringService

__all__ = [
    "LLMService",
    "VectorService", 
    "PredictionService",
    "CacheService",
    "MonitoringService"
]