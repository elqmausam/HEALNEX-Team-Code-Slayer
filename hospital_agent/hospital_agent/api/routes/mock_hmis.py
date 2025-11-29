

from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timedelta
import random
from typing import Optional

router = APIRouter()


VALID_API_KEY = "hmis_demo_key_12345"


def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key for mock endpoints"""
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    if token != VALID_API_KEY:
        raise HTTPException(401, "Invalid API key")
    
    return True


def generate_realistic_admissions():
    """Generate admission data that varies by time and day"""
    hour = datetime.now().hour
    day = datetime.now().weekday()
    
    # Base load
    base = 100
    
    # Time of day factor (peak hours 9am-5pm)
    if 9 <= hour <= 17:
        time_factor = 1.3
    elif 18 <= hour <= 22:
        time_factor = 1.1
    else:
        time_factor = 0.8
    
    # Weekend factor (lower on weekends)
    weekend_factor = 0.85 if day >= 5 else 1.0
    
    # Add random variation
    variation = random.uniform(0.9, 1.1)
    
    total = int(base * time_factor * weekend_factor * variation)
    return total


@router.get("/")
async def mock_hmis_root():
    """Mock HMIS API root"""
    return {
        "service": "Mock HMIS API",
        "version": "1.0.0",
        "status": "running",
        "note": "This is simulated data for testing",
        "api_key": "Use 'hmis_demo_key_12345' for testing"
    }


@router.get("/hospitals/{hospital_id}/admissions")
async def get_admissions(
    hospital_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get current admission statistics"""
    verify_api_key(authorization)
    
    total_admissions = generate_realistic_admissions()
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "current_admissions": total_admissions,
        "departments": {
            "emergency": {
                "patients": int(total_admissions * 0.30),
                "capacity": 50,
                "occupancy_rate": round(random.uniform(60, 95), 1),
                "wait_time_minutes": random.randint(30, 180)
            },
            "icu": {
                "patients": int(total_admissions * 0.12),
                "capacity": 20,
                "occupancy_rate": round(random.uniform(75, 100), 1),
                "ventilators_in_use": random.randint(8, 18)
            },
            "general_ward": {
                "patients": int(total_admissions * 0.45),
                "capacity": 120,
                "occupancy_rate": round(random.uniform(60, 85), 1)
            },
            "maternity": {
                "patients": int(total_admissions * 0.08),
                "capacity": 25,
                "occupancy_rate": round(random.uniform(40, 80), 1),
                "deliveries_today": random.randint(2, 8)
            },
            "pediatrics": {
                "patients": int(total_admissions * 0.05),
                "capacity": 15,
                "occupancy_rate": round(random.uniform(50, 90), 1)
            }
        },
        "bed_summary": {
            "total_beds": 230,
            "occupied_beds": total_admissions,
            "available_beds": 230 - total_admissions,
            "occupancy_percentage": round((total_admissions / 230) * 100, 2)
        },
        "er_metrics": {
            "wait_time_minutes": random.randint(30, 180),
            "triage_queue": random.randint(5, 25),
            "ambulance_arrivals_today": random.randint(15, 45),
            "critical_cases": random.randint(2, 8)
        },
        "alerts": [
            {
                "level": "warning",
                "message": "ER wait time exceeding target"
            } if random.random() > 0.7 else None,
            {
                "level": "info",
                "message": "ICU nearing capacity"
            } if random.random() > 0.8 else None
        ]
    }


@router.get("/hospitals/{hospital_id}/patient-demographics")
async def get_demographics(
    hospital_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get patient demographic breakdown"""
    verify_api_key(authorization)
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "age_groups": {
            "0-18": random.randint(15, 30),
            "19-35": random.randint(25, 45),
            "36-50": random.randint(30, 50),
            "51-65": random.randint(20, 40),
            "65+": random.randint(25, 50)
        },
        "gender": {
            "male": random.randint(45, 55),
            "female": random.randint(45, 55),
            "other": random.randint(0, 2)
        },
        "admission_types": {
            "emergency": random.randint(35, 50),
            "scheduled": random.randint(30, 45),
            "transfer": random.randint(10, 20),
            "referral": random.randint(5, 15)
        },
        "common_diagnoses": {
            "respiratory": random.randint(20, 35),
            "cardiac": random.randint(15, 25),
            "trauma": random.randint(10, 20),
            "gastrointestinal": random.randint(12, 22),
            "other": random.randint(30, 45)
        }
    }


@router.get("/hospitals/{hospital_id}/historical-admissions")
async def get_historical(
    hospital_id: str,
    days: int = 7,
    authorization: Optional[str] = Header(None)
):
    """Get historical admission data"""
    verify_api_key(authorization)
    
    if days > 90:
        days = 90  # Limit to 90 days
    
    history = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        
        # Add day-of-week patterns
        base = 120 if date.weekday() < 5 else 90
        
        # Add seasonal variation
        month = date.month
        if month in [6, 7, 8, 9]:  # Monsoon
            seasonal = 1.2
        elif month in [12, 1, 2]:  # Winter
            seasonal = 1.1
        else:
            seasonal = 1.0
        
        admissions = int(base * seasonal * random.uniform(0.85, 1.15))
        
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "admissions": admissions,
            "discharges": int(admissions * random.uniform(0.8, 1.0)),
            "average_los_days": round(random.uniform(2.5, 4.5), 1),
            "er_visits": int(admissions * random.uniform(0.4, 0.6)),
            "icu_admissions": int(admissions * random.uniform(0.10, 0.15)),
            "readmissions": int(admissions * random.uniform(0.05, 0.12))
        })
    
    return {
        "hospital_id": hospital_id,
        "period_days": days,
        "start_date": (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d"),
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "data": history,
        "summary": {
            "total_admissions": sum(d["admissions"] for d in history),
            "average_daily": round(sum(d["admissions"] for d in history) / days, 1),
            "peak_day": max(history, key=lambda x: x["admissions"])["date"]
        }
    }


@router.get("/hospitals/{hospital_id}/staffing")
async def get_staffing(
    hospital_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get current staffing levels"""
    verify_api_key(authorization)
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "shift": "morning" if 6 <= datetime.now().hour < 14 else "evening" if 14 <= datetime.now().hour < 22 else "night",
        "departments": {
            "emergency": {
                "doctors": random.randint(4, 8),
                "nurses": random.randint(10, 18),
                "required_doctors": 6,
                "required_nurses": 15
            },
            "icu": {
                "doctors": random.randint(2, 4),
                "nurses": random.randint(6, 10),
                "required_doctors": 3,
                "required_nurses": 8
            },
            "general_ward": {
                "doctors": random.randint(3, 6),
                "nurses": random.randint(12, 20),
                "required_doctors": 5,
                "required_nurses": 16
            }
        },
        "staffing_status": random.choice(["adequate", "adequate", "understaffed", "overstaffed"]),
        "call_list_available": random.randint(5, 15)
    }