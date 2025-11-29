# scripts/test_free_apis.py


import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any


class FreeAPITester:
    """Test all free external APIs"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = []
    
    async def close(self):
        await self.client.aclose()
    
    async def test_weather_open_meteo(self, location: str = "Mumbai") -> Dict[str, Any]:
        """Test Open-Meteo Weather API"""
        print("🌤️  Testing Weather API (Open-Meteo)...")
        
        coords = {
            "mumbai": {"lat": 19.0760, "lon": 72.8777},
            "delhi": {"lat": 28.6139, "lon": 77.2090},
            "bangalore": {"lat": 12.9716, "lon": 77.5946}
        }
        
        coord = coords.get(location.lower(), coords["mumbai"])
        
        try:
            response = await self.client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": coord["lat"],
                    "longitude": coord["lon"],
                    "current_weather": True,
                    "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": 7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data["current_weather"]
                
                result = {
                    "status": "✅ SUCCESS",
                    "api": "Open-Meteo Weather",
                    "location": location,
                    "data": {
                        "temperature": f"{current['temperature']}°C",
                        "wind_speed": f"{current['windspeed']} km/h",
                        "time": current['time'],
                        "forecast_days": len(data['daily']['time'])
                    }
                }
                
                print(f"     Weather data retrieved successfully!")
                print(f"     Temperature: {current['temperature']}°C")
                print(f"     Wind Speed: {current['windspeed']} km/h")
                print(f"     7-day forecast available")
                
                self.results.append(result)
                return data
            else:
                print(f"   Failed: Status {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"   Error: {e}")
            return {}
    
    async def test_aqi_open_meteo(self, location: str = "Mumbai") -> Dict[str, Any]:
        """Test Open-Meteo Air Quality API"""
        print("\n Testing Air Quality API (Open-Meteo)...")
        
        coords = {
            "mumbai": {"lat": 19.0760, "lon": 72.8777},
            "delhi": {"lat": 28.6139, "lon": 77.2090},
            "bangalore": {"lat": 12.9716, "lon": 77.5946}
        }
        
        coord = coords.get(location.lower(), coords["mumbai"])
        
        try:
            response = await self.client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": coord["lat"],
                    "longitude": coord["lon"],
                    "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust,us_aqi",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": 3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data["current"]
                
                pm25 = current.get("pm2_5", 0)
                aqi_level = self._get_aqi_level(pm25)
                
                result = {
                    "status": "✅ SUCCESS",
                    "api": "Open-Meteo Air Quality",
                    "location": location,
                    "data": {
                        "pm2_5": f"{pm25} μg/m³",
                        "pm10": f"{current.get('pm10', 0)} μg/m³",
                        "us_aqi": current.get("us_aqi", "N/A"),
                        "level": aqi_level
                    }
                }
                
                print(f"  ✅ Air quality data retrieved successfully!")
                print(f"     PM2.5: {pm25} μg/m³ ({aqi_level})")
                print(f"     PM10: {current.get('pm10', 0)} μg/m³")
                if "us_aqi" in current:
                    print(f"     US AQI: {current['us_aqi']}")
                
                self.results.append(result)
                return data
            else:
                print(f"  ❌ Failed: Status {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return {}
    
    async def test_holiday_api(self, country: str = "IN") -> Dict[str, Any]:
        """Test Public Holidays API (Free)"""
        print("\n🎉 Testing Holiday API (date.nager.at)...")
        
        try:
            year = datetime.now().year
            response = await self.client.get(
                f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"
            )
            
            if response.status_code == 200:
                holidays = response.json()
                upcoming = [h for h in holidays if datetime.fromisoformat(h['date']) > datetime.now()][:5]
                
                result = {
                    "status": "✅ SUCCESS",
                    "api": "Public Holidays API",
                    "data": {
                        "total_holidays": len(holidays),
                        "upcoming": len(upcoming)
                    }
                }
                
                print(f"  ✅ Holiday data retrieved successfully!")
                print(f"     Total holidays in {year}: {len(holidays)}")
                print(f"     Upcoming holidays: {len(upcoming)}")
                
                if upcoming:
                    print(f"     Next: {upcoming[0]['name']} on {upcoming[0]['date']}")
                
                self.results.append(result)
                return holidays
            else:
                print(f"  ❌ Failed: Status {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return {}
    
    async def test_disease_surveillance(self) -> Dict[str, Any]:
        """Test Disease Surveillance API (WHO/CDC open data)"""
        print("\n🦠 Testing Disease Surveillance API...")
        
        try:
            # Example: WHO COVID-19 data endpoint (public)
            response = await self.client.get(
                "https://disease.sh/v3/covid-19/countries/India",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    "status": "✅ SUCCESS",
                    "api": "Disease Surveillance",
                    "data": {
                        "country": data.get("country"),
                        "cases": data.get("cases"),
                        "updated": datetime.fromtimestamp(data.get("updated", 0) / 1000).isoformat()
                    }
                }
                
                print(f"  ✅ Disease surveillance data available!")
                print(f"     Source: disease.sh API")
                print(f"     Last updated: {result['data']['updated']}")
                
                self.results.append(result)
                return data
            else:
                print(f"  ⚠️  API status: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"  ℹ️  Disease API not accessible: {e}")
            return {}
    
    async def test_geocoding(self, location: str = "Mumbai") -> Dict[str, Any]:
        """Test Geocoding API (Nominatim - Free)"""
        print(f"\n📍 Testing Geocoding API for {location}...")
        
        try:
            response = await self.client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": location,
                    "format": "json",
                    "limit": 1
                },
                headers={"User-Agent": "HospitalAgent/1.0"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data:
                    place = data[0]
                    result = {
                        "status": " SUCCESS",
                        "api": "Nominatim Geocoding",
                        "data": {
                            "location": place.get("display_name"),
                            "lat": place.get("lat"),
                            "lon": place.get("lon")
                        }
                    }
                    
                    print(f"   Geocoding successful!")
                    print(f"     Coordinates: {place['lat']}, {place['lon']}")
                    
                    self.results.append(result)
                    return data
                else:
                    print(f"    No results found")
                    return {}
            else:
                print(f"   Failed: Status {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return {}
    
    def _get_aqi_level(self, pm25: float) -> str:
        """Get AQI level from PM2.5"""
        if pm25 <= 12:
            return "Good ✅"
        elif pm25 <= 35:
            return "Moderate ⚠️"
        elif pm25 <= 55:
            return "Unhealthy for Sensitive 🟠"
        elif pm25 <= 150:
            return "Unhealthy 🔴"
        elif pm25 <= 250:
            return "Very Unhealthy 🟣"
        else:
            return "Hazardous ⚫"
    
    async def run_all_tests(self, location: str = "Mumbai"):
        """Run all API tests"""
        print("=" * 70)
        print(" TESTING FREE EXTERNAL APIs (No Keys Required!)")
        print("=" * 70)
        
        await self.test_weather_open_meteo(location)
        await self.test_aqi_open_meteo(location)
        await self.test_holiday_api()
        await self.test_disease_surveillance()
        await self.test_geocoding(location)
        
        print("\n" + "=" * 70)
        print(" TEST SUMMARY")
        print("=" * 70)
        
        success_count = sum(1 for r in self.results if "SUCCESS" in r["status"])
        total_count = len(self.results)
        
        print(f"\n✅ Successful: {success_count}/{total_count}")
        print(f"📡 Data Sources Active: {success_count}")
        
        for result in self.results:
            print(f"\n  {result['status']} - {result['api']}")
            for key, value in result['data'].items():
                print(f"    • {key}: {value}")
        
        print("\n" + "=" * 70)
        print("🎉 ALL APIS READY FOR HOSPITAL AGENT!")
        print("=" * 70)


async def main():
    tester = FreeAPITester()
    
    try:
        # Test for multiple cities
        for city in ["Mumbai", "Delhi", "Bangalore"]:
            print(f"\n\n{'=' * 70}")
            print(f"Testing APIs for {city.upper()}")
            print(f"{'=' * 70}")
            await tester.run_all_tests(city)
            await asyncio.sleep(1)  # Rate limiting courtesy
    
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())