# hospital_agent/api/routes/documents_extended.py
"""
FIXED: Audio transcription endpoint
The issue was likely caching or not properly reading the audio file
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import io
from datetime import datetime
from openai import AsyncOpenAI
import os
import tempfile
import shutil

logger = logging.getLogger(__name__)

router = APIRouter()


class FormatNotesRequest(BaseModel):
    """Request to format clinical notes"""
    transcript: str
    note_type: str = "clinical_notes"


class GenerateDocumentRequest(BaseModel):
    """Request to generate a document"""
    title: str
    category: str
    content_type: str
    patient_context: Optional[str] = None


class ExportPDFRequest(BaseModel):
    """Request to export notes as PDF"""
    title: str
    content: str
    metadata: Optional[dict] = None


@router.post("/voice/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file from recording"),
    request: Request = None
):
    """
    Transcribe audio file to text using Whisper API
    FIXED: Properly handle file streams and avoid caching
    """
    temp_file_path = None
    
    try:
        # Validate file was uploaded
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Get OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured")
        
        client = AsyncOpenAI(api_key=openai_api_key)
        
        # CRITICAL FIX: Read the ENTIRE file content into memory FIRST
        content = await audio_file.read()
        
        # Validate file has content
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        
        # Calculate hash to verify uniqueness
        import hashlib
        content_hash = hashlib.md5(content).hexdigest()[:8]
        
        logger.info(f"📥 Received audio file: {audio_file.filename}, size: {len(content)} bytes, hash: {content_hash}")
        
        # Determine proper filename
        filename = audio_file.filename or "recording.webm"
        if not any(filename.endswith(ext) for ext in ['.webm', '.mp3', '.mp4', '.wav', '.m4a']):
            # Guess extension from content type
            content_type = audio_file.content_type or "audio/webm"
            if "mp4" in content_type:
                filename = "recording.mp4"
            elif "mp3" in content_type:
                filename = "recording.mp3"
            elif "wav" in content_type:
                filename = "recording.wav"
            else:
                filename = "recording.webm"
        
        logger.info(f"🎵 Processing as: {filename}")
        
        # Create a temporary file to ensure proper file handling
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
            logger.info(f"💾 Saved to temp file: {temp_file_path}")
        
        # Open and send to Whisper
        logger.info(f"🎤 Calling Whisper API for transcription...")
        
        with open(temp_file_path, 'rb') as audio_stream:
            # CRITICAL: Add timestamp to force new request
            start_time = datetime.now()
            
            transcript_response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, audio_stream, audio_file.content_type or "audio/webm"),
                response_format="text",
                language="en"
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"⏱️ Whisper API call took {elapsed:.2f} seconds")
        
        # Extract text from response
        if isinstance(transcript_response, str):
            transcript_text = transcript_response
        else:
            transcript_text = getattr(transcript_response, 'text', str(transcript_response))
        
        # Clean up transcript
        transcript_text = transcript_text.strip()
        
        logger.info(f"✅ Transcription completed: '{transcript_text[:100]}...' ({len(transcript_text)} chars)")
        logger.info(f"🔑 Audio hash: {content_hash} → Transcript hash: {hashlib.md5(transcript_text.encode()).hexdigest()[:8]}")
        
        return {
            "success": True,
            "transcript": transcript_text,
            "text": transcript_text,
            "filename": filename,
            "file_size": len(content),
            "content_hash": content_hash,
            "duration_seconds": len(content) / 16000,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Transcription error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.info(f"🗑️ Cleaned up temp file")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.post("/documents/format-clinical-notes")
async def format_clinical_notes(
    request_data: FormatNotesRequest,
    request: Request = None
):
    """
    Format raw transcript into structured clinical notes using GPT-4
    """
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured")
        
        client = AsyncOpenAI(api_key=openai_api_key)
        
        # Log what we're formatting
        logger.info(f"📝 Formatting transcript: '{request_data.transcript[:100]}...'")
        
        # Create prompt based on note type
        system_prompt = """You are a medical documentation assistant. Format the provided transcript into professional clinical notes following standard medical documentation practices.

Structure the notes with these sections (as applicable):
- **Chief Complaint (CC):** 
- **History of Present Illness (HPI):**
- **Physical Examination:**
- **Assessment:**
- **Plan:**

Use medical terminology appropriately and maintain HIPAA-compliant language. Format clearly with bullet points where appropriate."""

        user_prompt = f"""Format this clinical transcript into structured medical notes:

TRANSCRIPT:
{request_data.transcript}

Provide well-organized, professional clinical documentation."""

        logger.info("🤖 Calling GPT-4 for formatting...")
        
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Low temperature for consistent medical formatting
            max_tokens=2000
        )
        
        formatted_notes = response.choices[0].message.content
        
        logger.info(f"✅ Formatting completed: {len(formatted_notes)} characters")
        logger.info(f"📄 First 100 chars: '{formatted_notes[:100]}...'")
        
        return {
            "success": True,
            "formatted_notes": formatted_notes,
            "content": formatted_notes,  # Backward compatibility
            "original_transcript": request_data.transcript,
            "note_type": request_data.note_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Formatting error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Formatting failed: {str(e)}")


@router.post("/documents/generate")
async def generate_document(
    request_data: GenerateDocumentRequest,
    request: Request = None
):
    """
    Generate a medical document using AI based on parameters
    """
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=503, detail="OpenAI API key not configured")
        
        client = AsyncOpenAI(api_key=openai_api_key)
        
        # Create context-aware prompt
        system_prompt = f"""You are a medical documentation expert creating a {request_data.content_type} for the category: {request_data.category}.

Generate comprehensive, evidence-based medical documentation following current best practices and guidelines."""

        user_prompt = f"""Create a detailed medical document with the following specifications:

TITLE: {request_data.title}
CATEGORY: {request_data.category}
TYPE: {request_data.content_type}

{"ADDITIONAL CONTEXT: " + request_data.patient_context if request_data.patient_context else ""}

Generate a complete, professional document with appropriate sections, clear formatting, and evidence-based recommendations."""

        logger.info(f"📄 Generating document: {request_data.title}")
        
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=3000
        )
        
        content = response.choices[0].message.content
        
        # Extract keywords using simple method (could be enhanced)
        keywords = extract_keywords(content, request_data.title)
        
        logger.info(f"✅ Document generated: {len(content)} characters")
        
        return {
            "success": True,
            "content": content,
            "title": request_data.title,
            "category": request_data.category,
            "keywords": keywords,
            "document": {
                "id": f"doc_{int(datetime.now().timestamp())}",
                "title": request_data.title,
                "category": request_data.category,
                "content": content,
                "created_at": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Document generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/documents/export-pdf")
async def export_to_pdf(
    request_data: ExportPDFRequest,
    request: Request = None
):
    """
    Export document to PDF format
    """
    try:
        # Import PDF library (install with: pip install reportlab)
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="PDF library not installed. Run: pip install reportlab"
            )
        
        logger.info(f"📄 Generating PDF: {request_data.title}")
        
        # Create PDF in memory
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Container for PDF elements
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='#1a56db',
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        body_style = styles['BodyText']
        body_style.fontSize = 11
        body_style.leading = 14
        
        # Add title
        title = Paragraph(request_data.title, title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Add metadata if provided
        if request_data.metadata:
            metadata_text = f"Generated: {request_data.metadata.get('date', datetime.now().isoformat())}"
            if 'duration' in request_data.metadata:
                mins = request_data.metadata['duration'] // 60
                secs = request_data.metadata['duration'] % 60
                metadata_text += f" | Duration: {mins}:{secs:02d}"
            
            metadata_para = Paragraph(metadata_text, styles['Normal'])
            elements.append(metadata_para)
            elements.append(Spacer(1, 0.3 * inch))
        
        # Add content
        # Split content by paragraphs and format
        paragraphs = request_data.content.split('\n\n')
        for para_text in paragraphs:
            if para_text.strip():
                # Replace newlines with <br/> for ReportLab
                formatted_text = para_text.strip().replace('\n', '<br/>')
                para = Paragraph(formatted_text, body_style)
                elements.append(para)
                elements.append(Spacer(1, 0.1 * inch))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF bytes
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"✅ PDF exported: {len(pdf_bytes)} bytes")
        
        # Return PDF as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{request_data.title.replace(" ", "_")}.pdf"'
            }
        )
        
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        raise HTTPException(
            status_code=500,
            detail="PDF generation requires reportlab library. Install with: pip install reportlab"
        )
    except Exception as e:
        logger.error(f"❌ PDF export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


def extract_keywords(content: str, title: str) -> List[str]:
    """
    Extract keywords from content and title
    Simple implementation - could be enhanced with NLP
    """
    # Common medical stopwords to exclude
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'been', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'can'
    }
    
    # Combine title and first few words of content
    text = (title + ' ' + content[:500]).lower()
    
    # Extract words
    words = text.split()
    
    # Filter and count
    word_freq = {}
    for word in words:
        # Remove punctuation
        word = ''.join(c for c in word if c.isalnum())
        if len(word) > 3 and word not in stopwords:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top keywords
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    return [word for word, _ in keywords]