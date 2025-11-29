"""
Diagnostic script to test if your backend is caching responses
Run this to verify your transcription endpoint is working correctly

Usage:
    python test_transcription.py
"""

import requests
import io
import time

# Your backend URL
BASE_URL = "http://localhost:8000/api/v1"

def test_transcription_endpoint():
    """Test if the transcription endpoint is caching responses"""
    
    print("🧪 Testing Backend Transcription Endpoint\n")
    print("=" * 60)
    
    # Test 1: Check if endpoint is responsive
    print("\n1️⃣ Testing endpoint availability...")
    try:
        # Create dummy audio files with different sizes
        test_cases = [
            ("test1.webm", b"fake_audio_data_1" * 100, "First test audio"),
            ("test2.webm", b"fake_audio_data_2" * 150, "Second test audio"),
            ("test3.webm", b"fake_audio_data_3" * 200, "Third test audio"),
        ]
        
        results = []
        
        for filename, audio_data, description in test_cases:
            print(f"\n📤 Sending {description} ({len(audio_data)} bytes)...")
            
            # Create file-like object
            files = {
                'audio_file': (filename, io.BytesIO(audio_data), 'audio/webm')
            }
            
            # Send request
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/voice/transcribe",
                files=files
            )
            elapsed = time.time() - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Time: {elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                transcript = data.get('transcript', 'NO TRANSCRIPT')
                print(f"   📝 Transcript: '{transcript[:100]}...'")
                results.append({
                    'description': description,
                    'transcript': transcript,
                    'success': True
                })
            else:
                print(f"   ❌ Error: {response.text}")
                results.append({
                    'description': description,
                    'transcript': None,
                    'success': False
                })
            
            # Small delay between requests
            time.sleep(1)
        
        # Analysis
        print("\n" + "=" * 60)
        print("📊 ANALYSIS\n")
        
        successful_results = [r for r in results if r['success']]
        
        if len(successful_results) < 2:
            print("⚠️  Not enough successful responses to analyze")
            return
        
        # Check if all transcripts are identical
        transcripts = [r['transcript'] for r in successful_results]
        unique_transcripts = set(transcripts)
        
        print(f"Total requests: {len(test_cases)}")
        print(f"Successful: {len(successful_results)}")
        print(f"Unique transcripts: {len(unique_transcripts)}\n")
        
        if len(unique_transcripts) == 1:
            print("🚨 PROBLEM DETECTED: All transcripts are identical!")
            print("   This indicates caching or the endpoint is not processing")
            print("   the actual audio content.\n")
            print("   The transcript returned:")
            print(f"   '{transcripts[0][:200]}...'\n")
            print("💡 SOLUTION:")
            print("   1. Check backend logs for actual Whisper API calls")
            print("   2. Verify audio file is being read correctly")
            print("   3. Ensure no response caching middleware")
            print("   4. Use the fixed backend code provided")
        else:
            print("✅ LOOKS GOOD: Different transcripts for different inputs")
            print("   The backend is processing audio correctly.\n")
            for i, r in enumerate(successful_results, 1):
                print(f"   {i}. {r['description']}: '{r['transcript'][:50]}...'")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend at", BASE_URL)
        print("   Make sure your FastAPI server is running!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def check_backend_logs():
    """Instructions for checking backend logs"""
    print("\n" + "=" * 60)
    print("📋 HOW TO CHECK BACKEND LOGS\n")
    print("1. Look at your FastAPI terminal/console")
    print("2. You should see logs like:")
    print("   - '📥 Received audio file: recording.webm, size: XXXX bytes'")
    print("   - '🎤 Transcribing with Whisper API...'")
    print("   - '✅ Transcription completed: ...'")
    print("\n3. Each recording should show DIFFERENT transcript text")
    print("4. If you see the SAME transcript every time, the issue is:")
    print("   - Whisper is returning cached results")
    print("   - Audio file isn't being read properly")
    print("   - API key issues")


if __name__ == "__main__":
    test_transcription_endpoint()
    check_backend_logs()
    
    print("\n" + "=" * 60)
    print("🔍 NEXT STEPS:\n")
    print("1. Replace your documents_extended.py with the fixed version")
    print("2. Restart your FastAPI backend")
    print("3. Try recording again in the frontend")
    print("4. Check backend logs for different transcripts")
    print("5. If still having issues, the problem might be:")
    print("   - OpenAI API caching (unlikely)")
    print("   - Microphone recording same audio (check browser)")
    print("   - Frontend sending same audio blob repeatedly")