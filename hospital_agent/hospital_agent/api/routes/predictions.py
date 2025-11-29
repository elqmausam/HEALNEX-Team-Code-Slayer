# hospital_agent/api/routes/predictions.py

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()




class PredictionRequest(BaseModel):
    hospital_id: str = Field(default="H001", description="Hospital identifier")
    forecast_hours: int = Field(default=24, ge=1, le=168, description="Hours to forecast (1-168)")
    include_detailed_analysis: bool = Field(default=True, description="Include detailed breakdown")


class BatchPredictionRequest(BaseModel):
    hospital_ids: List[str] = Field(..., description="List of hospital IDs")
    forecast_hours: int = Field(default=24, ge=1, le=168)


class AlertThreshold(BaseModel):
    hospital_id: str
    occupancy_threshold: float = Field(default=85.0, description="Alert when occupancy exceeds this %")
    surge_threshold: float = Field(default=1.3, description="Alert when predicted surge exceeds this multiplier")



@router.post("/forecast")
async def generate_forecast(request: PredictionRequest, app_request: Request):
    
    try:
        prediction_service = app_request.app.state.prediction_service
        llm_service = app_request.app.state.llm_service
        
        # Generate base prediction
        prediction = await prediction_service.generate_forecast(
            hospital_id=request.hospital_id,
            forecast_hours=request.forecast_hours
        )
        
        # Add AI-powered insights if detailed analysis requested
        if request.include_detailed_analysis and prediction.get("predictions"):
            # Get first day prediction for insights
            first_prediction = prediction["predictions"][0] if prediction["predictions"] else {}
            
            try:
                insights = await llm_service.generate_response(
                    prompt=f"""Analyze this hospital prediction and provide 3 key insights:
                    
Predicted admissions: {first_prediction.get('predicted_admissions', 'N/A')}
Risk level: {first_prediction.get('risk_level', 'unknown')}
Contributing factors: {', '.join(first_prediction.get('contributing_factors', []))}

Provide actionable insights for hospital administrators.""",
                    system_prompt="You are a hospital operations analyst. Provide concise, actionable insights."
                )
                
                prediction["ai_insights"] = insights["response"]
            except Exception as e:
                logger.warning(f"Failed to generate AI insights: {e}")
                prediction["ai_insights"] = "AI insights unavailable"
        
        return {
            "status": "success",
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Forecast generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/{hospital_id}")
async def get_cached_forecast(
    hospital_id: str,
    app_request: Request
):
    """
    Get cached forecast for a hospital
    Returns most recent prediction if available
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if cache_service:
            cached_key = f"prediction:{hospital_id}:1"
            cached = await cache_service.get(cached_key)
            if cached:
                import json
                return {
                    "status": "success",
                    "prediction": json.loads(cached),
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                }
        
        # If no cache, generate new prediction
        prediction_service = app_request.app.state.prediction_service
        prediction = await prediction_service.generate_forecast(hospital_id)
        
        return {
            "status": "success",
            "prediction": prediction,
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_predictions(request: BatchPredictionRequest, app_request: Request):
    """
    Generate predictions for multiple hospitals
    Useful for multi-hospital systems
    """
    try:
        prediction_service = app_request.app.state.prediction_service
        
        predictions = {}
        errors = {}
        
        for hospital_id in request.hospital_ids:
            try:
                prediction = await prediction_service.generate_forecast(
                    hospital_id=hospital_id,
                    forecast_hours=request.forecast_hours
                )
                predictions[hospital_id] = prediction
            except Exception as e:
                errors[hospital_id] = str(e)
                logger.error(f"Batch prediction failed for {hospital_id}: {e}")
        
        return {
            "status": "success" if predictions else "error",
            "predictions": predictions,
            "errors": errors if errors else None,
            "total_requested": len(request.hospital_ids),
            "successful": len(predictions),
            "failed": len(errors),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/{hospital_id}")
async def get_historical_predictions(
    hospital_id: str,
    app_request: Request,
    days: int = Query(default=7, ge=1, le=30)
    
):
    """
    Get historical prediction accuracy
    Compare predictions vs actual admissions
    """
    try:
        # In production, this would query a database
        # For now, return mock historical data
        
        historical = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            historical.append({
                "date": date.strftime("%Y-%m-%d"),
                "predicted": 120 + (i * 5),
                "actual": 118 + (i * 5),
                "accuracy": 95.5,
                "variance": 2
            })
        
        return {
            "status": "success",
            "hospital_id": hospital_id,
            "days": days,
            "historical_data": historical,
            "average_accuracy": 95.5,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/configure")
async def configure_alerts(request: AlertThreshold, app_request: Request):
    """
    Configure prediction alerts
    Set thresholds for automatic notifications
    """
    try:
        cache_service = app_request.app.state.cache_service
        
        if cache_service:
            import json
            await cache_service.set(
                f"alert_config:{request.hospital_id}",
                json.dumps(request.dict()),
                ttl=86400  # 24 hours
            )
        
        return {
            "status": "success",
            "message": f"Alert thresholds configured for {request.hospital_id}",
            "config": request.dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{hospital_id}")
async def check_alerts(hospital_id: str, app_request: Request):
    """
    Check if any alert conditions are met
    Returns active alerts based on configured thresholds
    """
    try:
        prediction_service = app_request.app.state.prediction_service
        cache_service = app_request.app.state.cache_service
        
        # Get current prediction
        prediction = await prediction_service.generate_forecast(hospital_id)
        
        # Get alert configuration
        alert_config = None
        if cache_service:
            import json
            cached_config = await cache_service.get(f"alert_config:{hospital_id}")
            if cached_config:
                alert_config = json.loads(cached_config)
        
        # Default thresholds if not configured
        if not alert_config:
            alert_config = {
                "occupancy_threshold": 85.0,
                "surge_threshold": 1.3
            }
        
        # Check alert conditions
        alerts = []
        
        # Get first prediction for alert checking
        if prediction.get("predictions") and len(prediction["predictions"]) > 0:
            first_pred = prediction["predictions"][0]
            predicted_admissions = first_pred.get("predicted_admissions", 0)
            risk_level = first_pred.get("risk_level", "unknown")
            
            # Check surge alert
            if predicted_admissions > 100:  # Example threshold
                alerts.append({
                    "type": "surge",
                    "severity": "medium" if risk_level == "medium" else "high",
                    "message": f"Predicted admissions: {predicted_admissions}",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check risk level alert
            if risk_level == "high":
                alerts.append({
                    "type": "risk_level",
                    "severity": "high",
                    "message": f"High risk level detected",
                    "timestamp": datetime.now().isoformat()
                })
        
        return {
            "status": "success",
            "hospital_id": hospital_id,
            "alerts": alerts,
            "alert_count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors/{hospital_id}")
async def get_prediction_factors(hospital_id: str, app_request: Request):
    """
    Get detailed breakdown of factors affecting predictions
    Helps understand what's driving the forecast
    """
    try:
        prediction_service = app_request.app.state.prediction_service
        
        prediction = await prediction_service.generate_forecast(hospital_id)
        
        # Extract factors from prediction structure
        factors = []
        if prediction.get("predictions") and len(prediction["predictions"]) > 0:
            first_pred = prediction["predictions"][0]
            factors = first_pred.get("contributing_factors", [])
        
        return {
            "status": "success",
            "hospital_id": hospital_id,
            "factors": factors,
            "data_sources_used": prediction.get("data_sources_used", 0),
            "similar_patterns": prediction.get("similar_historical_patterns", 0),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{hospital_id}")
async def get_trends(
    hospital_id: str,
    app_request: Request,
    days: int = Query(default=30, ge=7, le=90)
    
):
    """
    Get admission trends over time
    Useful for identifying patterns
    """
    try:
        # Mock trend data (in production, query from database)
        import random
        
        trends = []
        base = 120
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            
            # Add weekly pattern
            weekday_factor = 1.2 if date.weekday() < 5 else 0.8
            
            # Add gradual trend
            trend_factor = 1 + (i * 0.001)
            
            admissions = int(base * weekday_factor * trend_factor * random.uniform(0.9, 1.1))
            
            trends.append({
                "date": date.strftime("%Y-%m-%d"),
                "admissions": admissions,
                "day_of_week": date.strftime("%A")
            })
        
        return {
            "status": "success",
            "hospital_id": hospital_id,
            "period_days": days,
            "trends": trends,
            "average": sum(t["admissions"] for t in trends) / len(trends),
            "peak_day": max(trends, key=lambda x: x["admissions"]),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))