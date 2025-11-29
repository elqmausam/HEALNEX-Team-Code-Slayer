

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio

router = APIRouter()


class PredictionDemoResponse(BaseModel):
    """Complete prediction with all data sources"""
    hospital_id: str
    location: str
    generated_at: str
    
    # Weather data
    current_weather: Dict[str, Any]
    weather_forecast: List[Dict[str, Any]]
    weather_risk: str
    
    # Air quality data
    current_aqi: Dict[str, Any]
    aqi_health_impact: str
    
    # Holiday impact
    upcoming_holidays: List[Dict[str, Any]]
    holiday_impact_days: int
    
    # Predictions
    surge_forecast: List[Dict[str, Any]]
    recommendations: List[str]
    
    # Metadata
    confidence_score: float
    data_sources_active: int
    total_data_sources: int


@router.get("/demo/{hospital_id}")
async def comprehensive_prediction_demo(
    hospital_id: str,
    location: str = "Mumbai",
    app_request: Request = None
):
    
    
    prediction_service = app_request.app.state.prediction_service
    
    # Fetch all data sources in parallel (FAST!)
    weather_task = prediction_service.fetch_weather_data(location, 7)
    aqi_task = prediction_service.fetch_aqi_data(location)
    holiday_task = prediction_service.fetch_holiday_calendar(location, 30)
    
    # Execute all requests concurrently
    weather_data, aqi_data, holidays = await asyncio.gather(
        weather_task, aqi_task, holiday_task
    )
    
    # Process weather data
    current_weather = {}
    weather_forecast = []
    weather_risk = "unknown"
    
    if weather_data:
        current = weather_data.get("current_weather", {})
        current_weather = {
            "temperature": f"{current.get('temperature', 'N/A')}°C",
            "wind_speed": f"{current.get('windspeed', 'N/A')} km/h",
            "wind_direction": f"{current.get('winddirection', 'N/A')}°",
            "time": current.get('time', 'N/A')
        }
        
        # Build 7-day forecast
        daily = weather_data.get("daily", {})
        if daily:
            for i in range(min(7, len(daily.get('time', [])))):
                weather_forecast.append({
                    "date": daily['time'][i],
                    "temp_max": f"{daily['temperature_2m_max'][i]}°C",
                    "temp_min": f"{daily['temperature_2m_min'][i]}°C",
                    "precipitation": f"{daily['precipitation_sum'][i]}mm",
                    "precip_probability": f"{daily.get('precipitation_probability_max', [0])[i]}%"
                })
        
        weather_risk = prediction_service._assess_weather_risk(weather_data)
    
    # Process AQI data
    current_aqi = {}
    aqi_health_impact = "unknown"
    
    if aqi_data:
        current = aqi_data.get("current", {})
        pm25 = current.get("pm2_5", 0)
        
        current_aqi = {
            "pm2_5": f"{pm25} μg/m³",
            "pm10": f"{current.get('pm10', 0)} μg/m³",
            "us_aqi": current.get("us_aqi", "N/A"),
            "co": f"{current.get('carbon_monoxide', 0)} μg/m³",
            "no2": f"{current.get('nitrogen_dioxide', 0)} μg/m³",
            "o3": f"{current.get('ozone', 0)} μg/m³"
        }
        
        aqi_info = prediction_service._interpret_aqi(pm25)
        aqi_health_impact = f"{aqi_info['level']} - {aqi_info['recommendation']}"
    
    # Process holiday data
    upcoming_holidays = []
    holiday_impact_days = 0
    
    if holidays:
        for holiday in holidays[:5]:  # Next 5 holidays
            upcoming_holidays.append({
                "name": holiday.get("name", "Holiday"),
                "date": holiday.get("date", "TBD"),
                "type": holiday.get("type", "public")
            })
            
            # Calculate impact window (3 days before to 2 days after)
            holiday_impact_days += 5
    
    # Generate surge predictions
    surge_forecast = []
    
    for day in range(7):
        date = datetime.now() + timedelta(days=day + 1)
        
        # Base prediction
        base_admissions = 50
        
        # Weather factor
        weather_factor = 1.0
        if weather_risk == "high_heat":
            weather_factor = 1.3
        elif weather_risk == "high_cold":
            weather_factor = 1.2
        elif weather_risk == "high_precipitation":
            weather_factor = 1.25
        
        # AQI factor
        aqi_factor = 1.0
        if aqi_data:
            pm25 = aqi_data.get("current", {}).get("pm2_5", 0)
            if pm25 > 150:
                aqi_factor = 1.4  # Hazardous air = more respiratory cases
            elif pm25 > 55:
                aqi_factor = 1.2  # Unhealthy air
        
        # Holiday factor
        holiday_factor = 1.0
        date_str = date.strftime("%Y-%m-%d")
        for holiday in holidays:
            if holiday.get("date") == date_str:
                holiday_factor = 1.15  # Slight increase on holidays
        
        # Calculate prediction
        predicted = int(base_admissions * weather_factor * aqi_factor * holiday_factor)
        
        # Determine risk level
        if predicted > 70:
            risk_level = "high"
        elif predicted > 60:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        surge_forecast.append({
            "date": date_str,
            "predicted_admissions": predicted,
            "risk_level": risk_level,
            "confidence": 0.78,
            "factors": {
                "weather_impact": f"{(weather_factor - 1) * 100:.0f}%",
                "aqi_impact": f"{(aqi_factor - 1) * 100:.0f}%",
                "holiday_impact": f"{(holiday_factor - 1) * 100:.0f}%"
            }
        })
    
    # Generate recommendations
    recommendations = []
    
    if weather_risk in ["high_heat", "high_cold"]:
        recommendations.append("⚠️ Prepare for weather-related admissions (heat stroke/hypothermia)")
    
    if aqi_data and aqi_data.get("current", {}).get("pm2_5", 0) > 55:
        recommendations.append("🌫️ Stock up on respiratory medications and equipment")
    
    if holiday_impact_days > 0:
        recommendations.append(f"🎉 Expect increased admissions around {len(upcoming_holidays)} upcoming holidays")
    
    recommendations.append("📊 Maintain 15-20% surge capacity for next 7 days")
    recommendations.append("👥 Consider flexible staffing schedules")
    
    # Calculate confidence and active sources
    data_sources_active = sum([
        1 if weather_data else 0,
        1 if aqi_data else 0,
        1 if holidays else 0,
        1,  # Seasonal patterns (always available)
        1,  # Historical data (simulated)
    ])
    
    total_data_sources = 7
    confidence_score = 0.65 + (data_sources_active / total_data_sources) * 0.25
    
    return PredictionDemoResponse(
        hospital_id=hospital_id,
        location=location,
        generated_at=datetime.now().isoformat(),
        current_weather=current_weather,
        weather_forecast=weather_forecast,
        weather_risk=weather_risk,
        current_aqi=current_aqi,
        aqi_health_impact=aqi_health_impact,
        upcoming_holidays=upcoming_holidays,
        holiday_impact_days=holiday_impact_days,
        surge_forecast=surge_forecast,
        recommendations=recommendations,
        confidence_score=confidence_score,
        data_sources_active=data_sources_active,
        total_data_sources=total_data_sources
    )


@router.get("/demo/{hospital_id}/simple")
async def simple_prediction_demo(
    hospital_id: str,
    location: str = "Mumbai",
    app_request: Request = None
):
    """
    📊 Simple 7-Day Surge Prediction
    Perfect for quick dashboard view
    """
    
    prediction_service = app_request.app.state.prediction_service
    
    # Quick parallel fetch
    weather_data, aqi_data = await asyncio.gather(
        prediction_service.fetch_weather_data(location, 7),
        prediction_service.fetch_aqi_data(location)
    )
    
    # Build simple forecast
    forecast = []
    
    for day in range(7):
        date = datetime.now() + timedelta(days=day + 1)
        
        # Simple calculation
        base = 50
        weather_boost = 1.1 if weather_data else 1.0
        aqi_boost = 1.15 if aqi_data and aqi_data.get("current", {}).get("pm2_5", 0) > 55 else 1.0
        
        predicted = int(base * weather_boost * aqi_boost)
        
        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "admissions": predicted,
            "trend": "↗️" if predicted > 55 else "→" if predicted > 45 else "↘️"
        })
    
    return {
        "hospital_id": hospital_id,
        "location": location,
        "forecast": forecast,
        "data_sources": {
            "weather": "✅" if weather_data else "❌",
            "air_quality": "✅" if aqi_data else "❌"
        }
    }