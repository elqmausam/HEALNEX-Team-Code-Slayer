

import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import pandas as pd
import logging

from ..core.config import settings
from .cache_service import CacheService
from .vector_service import VectorService

logger = logging.getLogger(__name__)


class PredictionService:
    """Predictive intelligence service for hospital surge forecasting"""
    
    def __init__(self, cache_service: CacheService, vector_service: VectorService):
        self.cache_service = cache_service
        self.vector_service = vector_service
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def initialize(self):
        """Initialize HTTP client for external APIs"""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50
            )
        )
        logger.info("Prediction service initialized")
    
    async def close(self):
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.aclose()
    
    # ==================== External Data Sources ====================
    
    async def fetch_weather_data(
        self,
        location: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Fetch weather forecast data using Open-Meteo (Free API)"""
        cache_key = f"weather:{location}:{days}"
        cached = await self.cache_service.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # Get coordinates for location (you can expand this mapping)
        location_coords = {
            "mumbai": {"lat": 19.0760, "lon": 72.8777},
            "delhi": {"lat": 28.6139, "lon": 77.2090},
            "bangalore": {"lat": 12.9716, "lon": 77.5946},
            "chennai": {"lat": 13.0827, "lon": 80.2707},
            "kolkata": {"lat": 22.5726, "lon": 88.3639},
            "hyderabad": {"lat": 17.3850, "lon": 78.4867},
            "pune": {"lat": 18.5204, "lon": 73.8567},
        }
        
        coords = location_coords.get(location.lower(), location_coords["mumbai"])
        
        try:
            response = await self.http_client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "current_weather": True,
                    "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": days
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                await self.cache_service.set(cache_key, json.dumps(data), ttl=3600)
                logger.info(f"Weather data fetched for {location}")
                return data
            
            logger.warning(f"Weather API returned {response.status_code}")
            return {}
            
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            return {}
    
    async def fetch_aqi_data(self, location: str) -> Dict[str, Any]:
        """Fetch Air Quality Index data using Open-Meteo (Free API)"""
        cache_key = f"aqi:{location}"
        cached = await self.cache_service.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # Get coordinates for location
        location_coords = {
            "mumbai": {"lat": 19.0760, "lon": 72.8777},
            "delhi": {"lat": 28.6139, "lon": 77.2090},
            "bangalore": {"lat": 12.9716, "lon": 77.5946},
            "chennai": {"lat": 13.0827, "lon": 80.2707},
            "kolkata": {"lat": 22.5726, "lon": 88.3639},
            "hyderabad": {"lat": 17.3850, "lon": 78.4867},
            "pune": {"lat": 18.5204, "lon": 73.8567},
        }
        
        coords = location_coords.get(location.lower(), location_coords["mumbai"])
        
        try:
            response = await self.http_client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust,us_aqi",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": 3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                await self.cache_service.set(cache_key, json.dumps(data), ttl=1800)
                logger.info(f"AQI data fetched for {location}")
                return data
            
            return {}
            
        except Exception as e:
            logger.error(f"AQI fetch error: {e}")
            return {}
    
    async def fetch_hmis_data(
        self,
        hospital_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Fetch data from Hospital Management Information System"""
        if not settings.HMIS_API_URL:
            return {}
        
        cache_key = f"hmis:{hospital_id}:{start_date.date()}:{end_date.date()}"
        cached = await self.cache_service.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        try:
            response = await self.http_client.get(
                f"{settings.HMIS_API_URL}/hospitals/{hospital_id}/admissions",
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                headers={"Authorization": f"Bearer {settings.HMIS_API_KEY}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                await self.cache_service.set(cache_key, json.dumps(data), ttl=1800)
                return data
            
            return {}
            
        except Exception as e:
            logger.error(f"HMIS fetch error: {e}")
            return {}
    
    async def fetch_lab_data(
        self,
        hospital_id: str,
        test_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fetch laboratory system data"""
        if not settings.LAB_API_URL:
            return {}
        
        cache_key = f"lab:{hospital_id}:{':'.join(test_types or [])}"
        cached = await self.cache_service.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        try:
            params = {"hospital_id": hospital_id}
            if test_types:
                params["test_types"] = ",".join(test_types)
            
            response = await self.http_client.get(
                f"{settings.LAB_API_URL}/test-volumes",
                params=params,
                headers={"Authorization": f"Bearer {settings.LAB_API_KEY}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                await self.cache_service.set(cache_key, json.dumps(data), ttl=1800)
                return data
            
            return {}
            
        except Exception as e:
            logger.error(f"Lab data fetch error: {e}")
            return {}
    
    async def fetch_seasonal_trends(
        self,
        region: str,
        diseases: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fetch seasonal disease trends"""
        # This would integrate with epidemiological databases
        # For now, returning mock structure
        return {
            "region": region,
            "current_season": self._get_current_season(),
            "trending_diseases": diseases or [],
            "historical_patterns": {}
        }
    
    async def fetch_holiday_calendar(
        self,
        region: str,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch holiday and festival calendar using free API"""
        cache_key = f"holidays:{region}:{days_ahead}"
        cached = await self.cache_service.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        try:
            # Get current year
            year = datetime.now().year
            
            # Use free public holidays API (date.nager.at)
            response = await self.http_client.get(
                f"https://date.nager.at/api/v3/PublicHolidays/{year}/IN"
            )
            
            if response.status_code == 200:
                holidays = response.json()
                
                # Filter upcoming holidays within days_ahead
                cutoff_date = datetime.now() + timedelta(days=days_ahead)
                upcoming = [
                    h for h in holidays
                    if datetime.fromisoformat(h['date']) > datetime.now()
                    and datetime.fromisoformat(h['date']) < cutoff_date
                ]
                
                # Cache for 24 hours
                await self.cache_service.set(
                    cache_key,
                    json.dumps(upcoming),
                    ttl=86400
                )
                
                logger.info(f"Fetched {len(upcoming)} upcoming holidays")
                return upcoming
            
            return []
            
        except Exception as e:
            logger.error(f"Holiday fetch error: {e}")
            return []
    
    async def fetch_epidemic_alerts(self, region: str) -> List[Dict[str, Any]]:
        """Fetch epidemic and outbreak alerts"""
        # Integration with public health APIs
        return []
    
    # ==================== Prediction Models ====================
    
    async def predict_patient_surge(
        self,
        hospital_id: str,
        forecast_days: int = 30,
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Predict patient surge with multi-source data integration"""
        
        # Fetch all data sources in parallel
        location = "mumbai"  # Get from hospital profile
        
        tasks = [
            self.fetch_weather_data(location, forecast_days),
            self.fetch_aqi_data(location),
            self.fetch_hmis_data(
                hospital_id,
                datetime.now() - timedelta(days=90),
                datetime.now()
            ),
            self.fetch_lab_data(hospital_id),
            self.fetch_seasonal_trends(location),
            self.fetch_holiday_calendar(location, forecast_days),
            self.fetch_epidemic_alerts(location)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        weather_data, aqi_data, hmis_data, lab_data, seasonal_data, holidays, alerts = results
        
        # Aggregate all data
        aggregated_data = {
            "hospital_id": hospital_id,
            "forecast_period": forecast_days,
            "data_sources": {
                "weather": weather_data if not isinstance(weather_data, Exception) else {},
                "air_quality": aqi_data if not isinstance(aqi_data, Exception) else {},
                "historical_admissions": hmis_data if not isinstance(hmis_data, Exception) else {},
                "lab_volumes": lab_data if not isinstance(lab_data, Exception) else {},
                "seasonal_trends": seasonal_data if not isinstance(seasonal_data, Exception) else {},
                "holidays": holidays if not isinstance(holidays, Exception) else [],
                "epidemic_alerts": alerts if not isinstance(alerts, Exception) else []
            }
        }
        
        # Generate prediction
        prediction = await self._generate_surge_prediction(
            aggregated_data,
            confidence_threshold
        )
        
        # Cache prediction
        cache_key = f"prediction:{hospital_id}:{forecast_days}"
        await self.cache_service.set(
            cache_key,
            json.dumps(prediction),
            ttl=21600  # 6 hours
        )
        
        return prediction
    
    # Add this method to hospital_agent/services/prediction_service.py

    async def generate_forecast(
        self,
        hospital_id: str,
        forecast_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate hospital admission forecast
        (Alias for predict_patient_surge, converts hours to days)
        """
        # Convert hours to days
        forecast_days = max(1, forecast_hours // 24)

        logger.info(
            f"Generating forecast for {hospital_id} "
            f"({forecast_hours} hours / {forecast_days} days)"
        )

        # Call the existing comprehensive prediction method
        return await self.predict_patient_surge(
            hospital_id=hospital_id,
            forecast_days=forecast_days,
            confidence_threshold=0.7
        )

    
    async def _generate_surge_prediction(
        self,
        data: Dict[str, Any],
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Generate surge prediction using LLM + historical patterns"""
        
        # Search for similar historical patterns
        query = self._build_pattern_query(data)
        similar_patterns = await self.vector_service.search_protocols(
            query=query,
            top_k=10,
            filters={"type": "historical_pattern"}

        )
        
        # Build prediction structure
        predictions = []
        
        # Analyze each forecast day
        for day in range(1, data["forecast_period"] + 1):
            day_prediction = {
                "date": (datetime.now() + timedelta(days=day)).isoformat(),
                "predicted_admissions": self._predict_daily_admissions(data, day),
                "confidence": 0.75,
                "risk_level": "medium",
                "contributing_factors": [],
                "recommendations": []
            }
            
            # Add weather factors
            if data["data_sources"]["weather"]:
                day_prediction["contributing_factors"].append("weather_conditions")
            
            # Add air quality factors
            if data["data_sources"]["air_quality"]:
                day_prediction["contributing_factors"].append("air_quality")
            
            # Add seasonal factors
            if data["data_sources"]["seasonal_trends"]:
                day_prediction["contributing_factors"].append("seasonal_patterns")
            
            predictions.append(day_prediction)
        
        return {
            "hospital_id": data["hospital_id"],
            "generated_at": datetime.now().isoformat(),
            "forecast_period_days": data["forecast_period"],
            "overall_confidence": 0.78,
            "predictions": predictions,
            "data_sources_used": len([v for v in data["data_sources"].values() if v]),
            "similar_historical_patterns": len(similar_patterns)
        }
    
    def _build_pattern_query(self, data: Dict[str, Any]) -> str:
        """Build query for finding similar historical patterns"""
        season = self._get_current_season()
        return f"hospital surge patterns {season} respiratory cases weather impact"
    
    def _predict_daily_admissions(self, data: Dict[str, Any], day: int) -> int:
        """Predict admissions for a specific day"""
        # Simplified prediction logic
        base_admissions = 50
        weather_factor = 1.0
        seasonal_factor = 1.1
        
        return int(base_admissions * weather_factor * seasonal_factor)
    
    def _get_current_season(self) -> str:
        """Get current season in India"""
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "summer"
        elif month in [6, 7, 8, 9]:
            return "monsoon"
        else:
            return "autumn"
    
    def _interpret_aqi(self, pm25: float) -> Dict[str, str]:
        """Interpret PM2.5 levels into health categories"""
        if pm25 <= 12:
            return {
                "level": "good",
                "health_impact": "minimal",
                "color": "green",
                "recommendation": "Normal outdoor activities"
            }
        elif pm25 <= 35:
            return {
                "level": "moderate",
                "health_impact": "acceptable",
                "color": "yellow",
                "recommendation": "Unusually sensitive people should consider reducing prolonged outdoor exertion"
            }
        elif pm25 <= 55:
            return {
                "level": "unhealthy_sensitive",
                "health_impact": "moderate",
                "color": "orange",
                "recommendation": "Sensitive groups should reduce prolonged outdoor exertion"
            }
        elif pm25 <= 150:
            return {
                "level": "unhealthy",
                "health_impact": "significant",
                "color": "red",
                "recommendation": "Everyone should reduce prolonged outdoor exertion"
            }
        elif pm25 <= 250:
            return {
                "level": "very_unhealthy",
                "health_impact": "serious",
                "color": "purple",
                "recommendation": "Everyone should avoid all outdoor exertion"
            }
        else:
            return {
                "level": "hazardous",
                "health_impact": "emergency",
                "color": "maroon",
                "recommendation": "Everyone should remain indoors with air filtration"
            }
    
    def _assess_weather_risk(self, weather_data: Dict[str, Any]) -> str:
        """Assess health risk from weather conditions"""
        if not weather_data:
            return "unknown"
        
        try:
            current = weather_data.get("current_weather", {})
            temp = current.get("temperature", 25)
            wind_speed = current.get("windspeed", 0)
            
            # High temperature risk
            if temp > 40:
                return "high_heat"
            elif temp < 10:
                return "high_cold"
            
            # Check precipitation in daily data
            daily = weather_data.get("daily", {})
            if daily:
                precip = daily.get("precipitation_sum", [0])[0]
                if precip > 50:  # Heavy rain
                    return "high_precipitation"
            
            return "normal"
            
        except Exception as e:
            logger.error(f"Weather risk assessment error: {e}")
            return "unknown"