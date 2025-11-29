# hospital_agent/api/routes/voice.py

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import io

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Pydantic Models
# ============================================

class TextToSpeechRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech", max_length=4096)
    voice: Optional[str] = Field(default="alloy", description="Voice type: alloy, echo, fable, onyx, nova, shimmer")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed (0.25-4.0)")
    format: Optional[str] = Field(default="mp3", description="Audio format: mp3, opus, aac, flac")


class TranscriptionResponse(BaseModel):
    status: str
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None
    timestamp: str


# ============================================
# Endpoints
# ============================================

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(default=None, description="Audio language (auto-detect if not specified)"),
    app_request: Request = None
):
    """
    Transcribe audio to text using Speech-to-Text
    
    Supports:
    - Medical voice notes
    - Patient reports
    - Doctor dictations
    
    Formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    """
    try:
        # Validate file type
        allowed_types = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/mp4", "audio/webm", "audio/m4a"]
        
        if audio_file.content_type not in allowed_types and not audio_file.filename.endswith(('.mp3', '.wav', '.m4a', '.mp4', '.webm')):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: mp3, wav, m4a, mp4, webm"
            )
        
        # Read audio file
        audio_data = await audio_file.read()
        
        if len(audio_data) > 25 * 1024 * 1024:  # 25MB limit
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size: 25MB"
            )
        
        # In production, use OpenAI Whisper or similar
        # For now, return mock transcription
        
        logger.info(f"Transcribing audio file: {audio_file.filename} ({len(audio_data)} bytes)")
        
        # Mock transcription (replace with actual Whisper API call)
        transcription = {
            "text": "Patient complaining of severe headache and dizziness. Blood pressure elevated at 150/95. Recommend immediate neurological consultation.",
            "language": language or "en",
            "duration": 15.5,
            "confidence": 0.95
        }
        
        return TranscriptionResponse(
            status="success",
            text=transcription["text"],
            language=transcription["language"],
            duration=transcription["duration"],
            confidence=transcription["confidence"],
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text-to-speech")
async def text_to_speech(
    request: TextToSpeechRequest,
    app_request: Request
):
    """
    Convert text to speech audio
    
    Useful for:
    - Reading alerts aloud
    - Accessibility features
    - Voice notifications
    """
    try:
        # In production, use OpenAI TTS or similar
        # For now, return mock audio response
        
        logger.info(f"Converting text to speech: {request.text[:50]}...")
        
        # Mock audio data (in production, call TTS API)
        # This would be actual audio bytes from TTS service
        mock_audio = b"MOCK_AUDIO_DATA_HERE"
        
        return StreamingResponse(
            io.BytesIO(mock_audio),
            media_type=f"audio/{request.format}",
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.format}"
            }
        )
    
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-command")
async def process_voice_command(
    audio_file: UploadFile = File(...),
    app_request: Request = None
):
    """
    Process voice commands for hands-free operation
    
    Examples:
    - "Show me today's admissions"
    - "What's the current ER wait time?"
    - "Generate prediction for tomorrow"
    """
    try:
        # Read audio
        audio_data = await audio_file.read()
        
        # Transcribe (mock for now)
        transcribed_text = "Show me today's admissions"
        
        # Process command with LLM
        llm_service = app_request.app.state.llm_service
        
        response = await llm_service.generate_response(
            prompt=f"""Process this voice command and provide a response:
            
Command: {transcribed_text}

Provide a clear, actionable response. If this is a data request, explain what data would be retrieved.""",
            system_prompt="You are a voice assistant for hospital staff. Respond clearly and concisely to voice commands."
        )
        
        return {
            "status": "success",
            "transcribed_command": transcribed_text,
            "response": response["response"],
            "action": "data_retrieval",  # or "navigation", "alert", etc.
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Voice command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/medical-dictation")
async def process_medical_dictation(
    audio_file: UploadFile = File(...),
    patient_id: Optional[str] = Form(default=None),
    note_type: Optional[str] = Form(default="general", description="Note type: general, progress, discharge, etc."),
    app_request: Request = None
):
    """
    Process medical dictation and format as clinical notes
    
    Converts voice recordings to structured medical notes
    """
    try:
        audio_data = await audio_file.read()
        
        # Transcribe (mock)
        transcribed = "Patient presents with acute myocardial infarction. Administered aspirin 325mg. Initiated cardiac monitoring. Consulted cardiology."
        
        # Format with LLM
        llm_service = app_request.app.state.llm_service
        
        formatted = await llm_service.generate_response(
            prompt=f"""Format this medical dictation into a structured clinical note:

Transcription: {transcribed}
Note Type: {note_type}
Patient ID: {patient_id or 'Not specified'}

Structure the note with:
- Chief Complaint
- Assessment
- Plan
- Medications Administered""",
            system_prompt="You are a medical documentation assistant. Format dictations into clear, structured clinical notes."
        )
        
        return {
            "status": "success",
            "patient_id": patient_id,
            "note_type": note_type,
            "raw_transcription": transcribed,
            "formatted_note": formatted["response"],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Medical dictation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-languages")
async def get_supported_languages():
    """
    Get list of supported languages for transcription
    """
    return {
        "status": "success",
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "Hindi"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ar", "name": "Arabic"}
        ]
    }


@router.get("/voices")
async def get_available_voices():
    """
    Get list of available TTS voices
    """
    return {
        "status": "success",
        "voices": [
            {
                "id": "alloy",
                "name": "Alloy",
                "gender": "neutral",
                "description": "Clear and professional"
            },
            {
                "id": "echo",
                "name": "Echo",
                "gender": "male",
                "description": "Warm and friendly"
            },
            {
                "id": "fable",
                "name": "Fable",
                "gender": "female",
                "description": "Expressive and engaging"
            },
            {
                "id": "onyx",
                "name": "Onyx",
                "gender": "male",
                "description": "Deep and authoritative"
            },
            {
                "id": "nova",
                "name": "Nova",
                "gender": "female",
                "description": "Energetic and clear"
            },
            {
                "id": "shimmer",
                "name": "Shimmer",
                "gender": "female",
                "description": "Soft and calm"
            }
        ]
    }


@router.post("/batch-transcribe")
async def batch_transcribe(
    files: list[UploadFile] = File(...),
    app_request: Request = None
):
    """
    Transcribe multiple audio files in batch
    Useful for processing multiple patient recordings
    """
    try:
        if len(files) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 files per batch"
            )
        
        results = []
        
        for file in files:
            try:
                audio_data = await file.read()
                
                # Mock transcription
                result = {
                    "filename": file.filename,
                    "status": "success",
                    "text": f"Transcription for {file.filename}",
                    "duration": 10.0,
                    "confidence": 0.92
                }
                results.append(result)
            
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "total_files": len(files),
            "successful": len([r for r in results if r["status"] == "success"]),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))