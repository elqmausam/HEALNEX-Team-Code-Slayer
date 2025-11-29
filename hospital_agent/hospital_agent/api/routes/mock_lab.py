

from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timedelta
import random
from typing import Optional, List

router = APIRouter()


VALID_API_KEY = "lab_demo_key_12345"


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


@router.get("/")
async def mock_lab_root():
    """Mock Lab API root"""
    return {
        "service": "Mock Laboratory API",
        "version": "1.0.0",
        "status": "running",
        "note": "This is simulated data for testing",
        "api_key": "Use 'lab_demo_key_12345' for testing"
    }


@router.get("/test-volumes")
async def get_test_volumes(
    hospital_id: str = "HOSP001",
    authorization: Optional[str] = Header(None)
):
    """Get laboratory test volumes and statistics"""
    verify_api_key(authorization)
    
    hour = datetime.now().hour
    # Peak hours factor (more tests during day shift)
    peak_multiplier = 1.5 if 9 <= hour <= 16 else 0.7
    
    pending_base = int(random.randint(200, 400) * peak_multiplier)
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "pending_tests": pending_base,
            "completed_today": random.randint(400, 700),
            "in_progress": random.randint(50, 150),
            "average_turnaround_hours": round(random.uniform(2.5, 6.0), 1),
            "critical_results_pending": random.randint(0, 5)
        },
        "test_categories": {
            "hematology": {
                "name": "Blood Tests (CBC, Hemoglobin, etc.)",
                "pending": int(pending_base * 0.35),
                "completed_today": random.randint(150, 250),
                "in_progress": random.randint(20, 50),
                "turnaround_hours": round(random.uniform(1.5, 3.0), 1),
                "critical_alerts": random.randint(0, 2)
            },
            "biochemistry": {
                "name": "Clinical Chemistry (Glucose, Liver function, etc.)",
                "pending": int(pending_base * 0.30),
                "completed_today": random.randint(120, 200),
                "in_progress": random.randint(15, 40),
                "turnaround_hours": round(random.uniform(2.0, 4.0), 1),
                "critical_alerts": random.randint(0, 3)
            },
            "microbiology": {
                "name": "Cultures & Sensitivity",
                "pending": int(pending_base * 0.15),
                "completed_today": random.randint(50, 100),
                "in_progress": random.randint(10, 30),
                "turnaround_hours": round(random.uniform(24.0, 72.0), 1),
                "critical_alerts": random.randint(0, 1)
            },
            "radiology": {
                "name": "X-Ray, CT, MRI",
                "pending": int(pending_base * 0.10),
                "completed_today": random.randint(40, 80),
                "in_progress": random.randint(5, 15),
                "turnaround_hours": round(random.uniform(1.0, 2.5), 1),
                "critical_alerts": 0
            },
            "covid_pcr": {
                "name": "COVID-19 PCR Testing",
                "pending": int(pending_base * 0.07),
                "completed_today": random.randint(30, 80),
                "in_progress": random.randint(10, 25),
                "turnaround_hours": round(random.uniform(4.0, 8.0), 1),
                "critical_alerts": 0
            },
            "pathology": {
                "name": "Tissue Analysis & Biopsies",
                "pending": int(pending_base * 0.03),
                "completed_today": random.randint(10, 30),
                "in_progress": random.randint(5, 15),
                "turnaround_hours": round(random.uniform(48.0, 120.0), 1),
                "critical_alerts": random.randint(0, 1)
            }
        },
        "equipment_status": {
            "analyzers_operational": random.randint(8, 10),
            "analyzers_total": 10,
            "ct_scanners": random.choice(["operational", "operational", "maintenance"]),
            "mri_machines": random.choice(["operational", "operational"]),
            "xray_machines": random.choice(["operational", "operational", "operational"])
        },
        "staffing": {
            "technicians_on_duty": random.randint(15, 25),
            "pathologists_available": random.randint(3, 6),
            "radiologists_available": random.randint(2, 4)
        },
        "alerts": {
            "backlog_alert": pending_base > 300,
            "critical_results": random.randint(0, 5),
            "equipment_maintenance_due": random.choice([True, False, False, False])
        }
    }


@router.get("/historical-volumes")
async def get_historical_volumes(
    days: int = 7,
    hospital_id: str = "HOSP001",
    authorization: Optional[str] = Header(None)
):
    """Get historical lab test volumes"""
    verify_api_key(authorization)
    
    if days > 90:
        days = 90
    
    history = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        
        # Weekday pattern
        is_weekday = date.weekday() < 5
        base = 600 if is_weekday else 350
        
        # Add variation
        total_tests = int(base * random.uniform(0.85, 1.15))
        
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "total_tests": total_tests,
            "completed": int(total_tests * random.uniform(0.90, 0.98)),
            "average_turnaround": round(random.uniform(3.0, 6.0), 1),
            "critical_results": random.randint(2, 12),
            "hematology": int(total_tests * 0.35),
            "biochemistry": int(total_tests * 0.30),
            "microbiology": int(total_tests * 0.15),
            "radiology": int(total_tests * 0.10),
            "other": int(total_tests * 0.10)
        })
    
    return {
        "hospital_id": hospital_id,
        "period_days": days,
        "data": history,
        "summary": {
            "total_tests": sum(d["total_tests"] for d in history),
            "average_daily": round(sum(d["total_tests"] for d in history) / days, 1),
            "peak_day": max(history, key=lambda x: x["total_tests"])["date"]
        }
    }


@router.get("/critical-results")
async def get_critical_results(
    hospital_id: str = "HOSP001",
    authorization: Optional[str] = Header(None)
):
    """Get pending critical lab results"""
    verify_api_key(authorization)
    
    critical_tests = []
    
    # Generate some random critical results
    num_critical = random.randint(0, 5)
    
    test_types = [
        ("Hemoglobin", "hematology", "Critically low: 5.2 g/dL"),
        ("Potassium", "biochemistry", "Critically high: 6.8 mmol/L"),
        ("Troponin", "biochemistry", "Elevated: 2.4 ng/mL"),
        ("White Blood Cell", "hematology", "Critically high: 45,000 /µL"),
        ("Creatinine", "biochemistry", "Elevated: 4.5 mg/dL"),
        ("Blood Culture", "microbiology", "Positive for gram-negative bacteria")
    ]
    
    for i in range(num_critical):
        test = random.choice(test_types)
        critical_tests.append({
            "test_id": f"CRIT-{random.randint(1000, 9999)}",
            "test_name": test[0],
            "category": test[1],
            "result": test[2],
            "patient_location": random.choice(["ER", "ICU", "General Ward", "CCU"]),
            "ordered_time": (datetime.now() - timedelta(hours=random.randint(1, 6))).isoformat(),
            "priority": "CRITICAL",
            "notified": random.choice([True, False])
        })
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "critical_count": len(critical_tests),
        "results": critical_tests
    }


@router.get("/pending-specimens")
async def get_pending_specimens(
    hospital_id: str = "HOSP001",
    authorization: Optional[str] = Header(None)
):
    """Get specimens awaiting processing"""
    verify_api_key(authorization)
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "pending_specimens": {
            "blood": random.randint(20, 60),
            "urine": random.randint(15, 40),
            "tissue": random.randint(5, 15),
            "swabs": random.randint(10, 30),
            "other": random.randint(5, 20)
        },
        "oldest_specimen_age_hours": round(random.uniform(0.5, 24.0), 1),
        "urgent_specimens": random.randint(5, 15),
        "processing_queue": {
            "immediate": random.randint(3, 10),
            "urgent": random.randint(8, 20),
            "routine": random.randint(20, 50)
        }
    }


@router.get("/equipment-status")
async def get_equipment_status(
    hospital_id: str = "HOSP001",
    authorization: Optional[str] = Header(None)
):
    """Get lab equipment operational status"""
    verify_api_key(authorization)
    
    equipment = [
        {"name": "Hematology Analyzer #1", "status": random.choice(["operational", "operational", "operational", "maintenance"])},
        {"name": "Hematology Analyzer #2", "status": random.choice(["operational", "operational", "operational"])},
        {"name": "Chemistry Analyzer #1", "status": random.choice(["operational", "operational", "operational"])},
        {"name": "Chemistry Analyzer #2", "status": random.choice(["operational", "operational", "maintenance"])},
        {"name": "PCR Machine", "status": random.choice(["operational", "operational", "calibration"])},
        {"name": "CT Scanner", "status": random.choice(["operational", "operational", "maintenance"])},
        {"name": "MRI Machine", "status": random.choice(["operational", "operational"])},
        {"name": "X-Ray #1", "status": "operational"},
        {"name": "X-Ray #2", "status": random.choice(["operational", "operational", "maintenance"])},
        {"name": "Microscope Station #1", "status": "operational"},
    ]
    
    operational = sum(1 for e in equipment if e["status"] == "operational")
    
    return {
        "hospital_id": hospital_id,
        "timestamp": datetime.now().isoformat(),
        "equipment": equipment,
        "summary": {
            "total_equipment": len(equipment),
            "operational": operational,
            "maintenance": sum(1 for e in equipment if e["status"] == "maintenance"),
            "calibration": sum(1 for e in equipment if e["status"] == "calibration"),
            "operational_percentage": round((operational / len(equipment)) * 100, 1)
        }
    }