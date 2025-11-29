# test_multi_agent_negotiation.py
"""
Test script for multi-agent hospital negotiation
Simulates Hospital A detecting surge and negotiating with Hospitals B & C
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_scenario_1_surge_detection():
    """
    Scenario 1: Hospital A detects surge and initiates negotiation
    """
    print_section("SCENARIO 1: SURGE DETECTION & AUTO-NEGOTIATION")
    
    print("🏥 Hospital A: Detecting surge pattern...")
    
    # Step 1: Hospital A generates forecast
    forecast_request = {
        "hospital_id": "H001",
        "forecast_hours": 72,  # 3 days
        "include_detailed_analysis": True
    }
    
    print("\n📊 Generating surge forecast...")
    response = requests.post(
        f"{BASE_URL}/api/v1/predictions/forecast",
        json=forecast_request
    )
    
    if response.status_code == 200:
        forecast = response.json()
        print("✅ Forecast generated successfully!")
        
        # Check if surge is predicted
        predictions = forecast.get("prediction", {}).get("predictions", [])
        if predictions:
            first_day = predictions[0]
            predicted_admissions = first_day.get("predicted_admissions", 0)
            
            print(f"\n🚨 SURGE DETECTED!")
            print(f"   Predicted admissions: {predicted_admissions}")
            print(f"   Risk level: {first_day.get('risk_level', 'unknown')}")
            print(f"   Contributing factors: {', '.join(first_day.get('contributing_factors', []))}")
            
            # If surge detected, start negotiation
            if predicted_admissions > 100:  # Threshold for surge
                print("\n🤖 Hospital A Agent: Initiating autonomous negotiation...")
                return True, predicted_admissions
    
    return False, 0


def test_scenario_2_multi_hospital_negotiation():
    """
    Scenario 2: Complete multi-hospital negotiation with fake hospitals
    """
    print_section("SCENARIO 2: MULTI-HOSPITAL AUTONOMOUS NEGOTIATION")
    
    print("🏥 Hospital A (H001): I'm predicting 180 respiratory cases.")
    print("   Need: 8 ventilators + 2 pulmonologists")
    print("   Urgency: HIGH")
    print("   Budget: ₹500,000")
    
    time.sleep(2)
    
    # Start negotiation with fake scenario
    negotiation_request = {
        "requesting_hospital": "H001",
        "num_offering_hospitals": 3,  # Generate 3 fake hospitals (B, C, D)
        "resource_type": "ventilators",
        "quantity": 8,
        "scenario_type": "urgent",  # This is an urgent situation
        "urgency": "high"
    }
    
    print("\n📢 Broadcasting request to hospital network...")
    print("   Waiting for offers from Hospital B, C, D...")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/autonomous-negotiation/run-fake-scenario",
        json=negotiation_request
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n✅ Negotiation workflow complete!")
        print(f"   Status: {result.get('status')}")
        print(f"   Total time: {result.get('total_time_seconds', 0):.1f} seconds")
        
        # Show contract details
        contract = result.get("contract")
        if contract:
            print("\n📜 CONTRACT FINALIZED:")
            print(f"   Contract ID: {contract.get('contract_id')}")
            print(f"   Supplier: {contract.get('supplying_hospital')}")
            print(f"   Resource: {contract.get('quantity')} {contract.get('resource_type')}")
            print(f"   Total Price: ₹{contract.get('total_price'):,}")
            print(f"   Delivery: {contract.get('delivery_deadline')}")
            
            # Show negotiation summary
            summary = contract.get('negotiation_summary', {})
            print(f"\n💰 NEGOTIATION SUMMARY:")
            print(f"   Original price: ₹{summary.get('original_price', 0):,}")
            print(f"   Final price: ₹{summary.get('final_price', 0):,}")
            print(f"   Savings: ₹{summary.get('savings', 0):,}")
            print(f"   Rounds: {summary.get('rounds', 0)}")
        
        # Show notification
        notification = result.get("notification")
        if notification:
            print(f"\n🔔 RING! RING! {notification.get('title')}")
            print(f"   {notification.get('message')}")
            print(f"   Action required: {notification.get('action_required')}")
        
        return True
    
    else:
        print(f"❌ Negotiation failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_scenario_3_manual_multi_agent():
    """
    Scenario 3: Manual step-by-step multi-agent interaction
    Shows the detailed conversation between agents
    """
    print_section("SCENARIO 3: DETAILED MULTI-AGENT CONVERSATION")
    
    print("Step 1: Hospital A broadcasts need")
    print("-" * 60)
    
    # Hospital A starts negotiation
    print("\n🏥 Hospital A Agent:")
    print("   'I'm predicting 180 respiratory cases Nov 12-14.'")
    print("   'Need 8 ventilators and 2 pulmonologists.'")
    print("   'Max budget: ₹400,000'")
    
    negotiation_request = {
        "requesting_hospital": "H001",
        "resource_type": "ventilators",
        "quantity": 8,
        "urgency": "critical",
        "max_budget": 400000,
        "delivery_deadline": (datetime.now() + timedelta(days=3)).isoformat()
    }
    
    # Start negotiation (in background)
    response = requests.post(
        f"{BASE_URL}/api/v1/autonomous-negotiation/negotiate",
        json=negotiation_request
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Broadcast sent!")
        print(f"   Check notifications at: {result.get('check_notifications_at')}")
        
        # Simulate Hospital B responding
        time.sleep(2)
        print("\nStep 2: Hospital B receives broadcast and responds")
        print("-" * 60)
        
        print("\n🏥 Hospital B Agent:")
        print("   'I can loan 3 ventilators for 72 hours.'")
        print("   'Rate: ₹5,000/day/unit = ₹15,000/day total'")
        print("   'Need them back by Nov 15.'")
        
        offer_b = {
            "offering_hospital": "H002",
            "requesting_hospital": "H001",
            "resource_type": "ventilators",
            "quantity": 3,
            "unit_price": 15000,  # 3 days * 5000/day
            "delivery_time_hours": 4,
            "quality_certification": "ISO 13485",
            "additional_notes": "Premium ventilators with IoT monitoring"
        }
        
        response_b = requests.post(
            f"{BASE_URL}/api/v1/autonomous-negotiation/submit-offer",
            json=offer_b
        )
        
        if response_b.status_code == 200:
            offer_result = response_b.json()
            print(f"\n✅ Hospital B offer submitted: {offer_result.get('offer_id')}")
            print(f"   Total: ₹{offer_result.get('total_price'):,}")
        
        # Simulate Hospital C responding
        time.sleep(2)
        print("\nStep 3: Hospital C receives broadcast and responds")
        print("-" * 60)
        
        print("\n🏥 Hospital C Agent:")
        print("   'I can provide 5 ventilators for 7 days.'")
        print("   'Rate: ₹4,500/day/unit = ₹22,500/day total'")
        print("   'Plus Dr. Mehta (pulmonologist) available Nov 12-13.'")
        print("   'Doctor fee: ₹25,000/day + accommodation'")
        
        offer_c = {
            "offering_hospital": "H003",
            "requesting_hospital": "H001",
            "resource_type": "ventilators",
            "quantity": 5,
            "unit_price": 31500,  # 7 days * 4500/day
            "delivery_time_hours": 6,
            "quality_certification": "FDA Approved",
            "additional_notes": "Includes Dr. Mehta (pulmonologist) for 2 days @ ₹25k/day"
        }
        
        response_c = requests.post(
            f"{BASE_URL}/api/v1/autonomous-negotiation/submit-offer",
            json=offer_c
        )
        
        if response_c.status_code == 200:
            offer_result = response_c.json()
            print(f"\n✅ Hospital C offer submitted: {offer_result.get('offer_id')}")
            print(f"   Total: ₹{offer_result.get('total_price'):,}")
        
        # Wait and check for notifications
        print("\nStep 4: Waiting for negotiation to complete...")
        print("-" * 60)
        print("   (In production, this happens automatically)")
        print("   Agents are evaluating offers and negotiating...")
        
        time.sleep(5)
        
        # Check notifications
        notif_response = requests.get(
            f"{BASE_URL}/api/v1/autonomous-negotiation/notifications/H001"
        )
        
        if notif_response.status_code == 200:
            notif_result = notif_response.json()
            
            if notif_result.get("status") == "success":
                print("\n🔔 RING! RING! DING! DING!")
                print("   Negotiation complete!")
                
                notification = notif_result.get("notification")
                if notification:
                    print(f"\n   {notification.get('title')}")
                    print(f"   {notification.get('message')}")
            else:
                print(f"\n⏳ Status: {notif_result.get('message')}")
        
        return True
    
    else:
        print(f"❌ Failed to start negotiation: {response.text}")
        return False


def test_workflow_visualization():
    """Test: Get workflow graph"""
    print_section("WORKFLOW VISUALIZATION")
    
    response = requests.get(f"{BASE_URL}/api/v1/autonomous-negotiation/workflow-graph")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Workflow graph retrieved!")
        print(f"\n{result.get('graph')}")
        print(f"\nView at: {result.get('view_at')}")
        return True
    
    return False


def test_negotiation_stats():
    """Test: Get negotiation statistics"""
    print_section("NEGOTIATION STATISTICS")
    
    response = requests.get(f"{BASE_URL}/api/v1/autonomous-negotiation/stats")
    
    if response.status_code == 200:
        result = response.json()
        stats = result.get("stats", {})
        
        print("📊 Overall Statistics:")
        print(f"   Total negotiations: {stats.get('total_negotiations')}")
        print(f"   Success rate: {stats.get('success_rate')*100:.1f}%")
        print(f"   Average savings: {stats.get('average_savings_percent')}%")
        print(f"   Avg negotiation rounds: {stats.get('average_negotiation_rounds')}")
        print(f"   Avg time: {stats.get('average_time_minutes')} minutes")
        print(f"   Most negotiated: {stats.get('most_negotiated_resource')}")
        return True
    
    return False


def main():
    """Run all tests"""
    print("\n" + "🏥"*40)
    print("  HOSPITAL MULTI-AGENT NEGOTIATION TEST SUITE")
    print("🏥"*40)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server not healthy. Please start the application.")
            return
        print("✅ Server is healthy!")
    except Exception as e:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print(f"   Make sure the application is running: uvicorn main:app")
        return
    
    # Run test scenarios
    tests = [
        ("Workflow Visualization", test_workflow_visualization),
        ("Scenario 1: Surge Detection", test_scenario_1_surge_detection),
        ("Scenario 2: Full Auto-Negotiation", test_scenario_2_multi_hospital_negotiation),
        ("Scenario 3: Manual Multi-Agent", test_scenario_3_manual_multi_agent),
        ("Statistics Dashboard", test_negotiation_stats),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            print(f"Running: {test_name}")
            print('='*80)
            
            result = test_func()
            results.append((test_name, "✅ PASSED" if result else "⚠️  WARNING"))
            
            time.sleep(1)
        
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            results.append((test_name, "❌ FAILED"))
    
    # Summary
    print_section("TEST SUMMARY")
    
    for test_name, status in results:
        print(f"   {status}: {test_name}")
    
    passed = sum(1 for _, status in results if "PASSED" in status)
    total = len(results)
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-agent system is working!")
    
    print("\n" + "🏥"*40 + "\n")


if __name__ == "__main__":
    main()