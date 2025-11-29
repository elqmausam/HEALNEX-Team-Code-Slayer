# hospital_agent/services/llm_service.py

import os
import json
import logging
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
import asyncio

# Import LLM clients
try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

logger = logging.getLogger(__name__)


class LLMService:
    """
    Universal LLM service supporting multiple providers:
    - Anthropic Claude
    - Google Gemini
    - OpenAI GPT
    """
    
    def __init__(self, cache_service=None):
        self.cache_service = cache_service
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        self.initialized = False
        
        # Initialize the appropriate client
        self._init_client()
    
    def _init_client(self):
        """Initialize LLM client based on provider"""
        
        try:
            if self.provider == "anthropic":
                if not AsyncAnthropic:
                    raise ImportError("anthropic package not installed. Run: pip install anthropic")
                
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in environment")
                
                self.client = AsyncAnthropic(api_key=api_key)
                self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
                logger.info(f"✅ LLM Service initialized with Anthropic Claude: {self.model}")
            
            elif self.provider == "gemini":
                if not genai:
                    raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
                
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not found in environment")
                
                genai.configure(api_key=api_key)
                self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                self.client = genai.GenerativeModel(self.model_name)
                logger.info(f"✅ LLM Service initialized with Google Gemini: {self.model_name}")
            
            elif self.provider == "openai":
                if not AsyncOpenAI:
                    raise ImportError("openai package not installed. Run: pip install openai")
                
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment")
                
                self.client = AsyncOpenAI(api_key=api_key)
                self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
                logger.info(f"✅ LLM Service initialized with OpenAI: {self.model}")
            
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
            self.initialized = True
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM Service: {e}")
            self.initialized = False
            raise
    
    async def initialize(self):
        """Initialize LLM service (async initialization if needed)"""
        if not self.initialized:
            self._init_client()
        logger.info("LLM Service ready")
        return True
    
    async def health_check(self) -> bool:
        """Check if LLM service is healthy"""
        if not self.initialized:
            return False
        
        try:
            # Quick test to verify the client is working
            if self.provider == "gemini":
                # Gemini doesn't need async health check
                return True
            elif self.provider == "anthropic":
                # For Claude, we can check if client exists
                return self.client is not None
            elif self.provider == "openai":
                # For OpenAI, we can check if client exists
                return self.client is not None
            
            return True
        
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return False
    
    async def close(self):
        """Cleanup resources"""
        logger.info("Closing LLM Service...")
        self.initialized = False
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM
        
        Args:
            prompt: User's message
            system_prompt: System instructions
            conversation_history: Previous messages
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with response and metadata
        """
        
        if self.provider == "anthropic":
            return await self._generate_claude(prompt, system_prompt, conversation_history, **kwargs)
        elif self.provider == "gemini":
            return await self._generate_gemini(prompt, system_prompt, conversation_history, **kwargs)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, system_prompt, conversation_history, **kwargs)
    
    async def generate_streaming_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM
        
        Yields:
            String chunks of the response
        """
        
        if self.provider == "anthropic":
            async for chunk in self._stream_claude(prompt, system_prompt, conversation_history, **kwargs):
                yield chunk
        elif self.provider == "gemini":
            async for chunk in self._stream_gemini(prompt, system_prompt, conversation_history, **kwargs):
                yield chunk
        elif self.provider == "openai":
            async for chunk in self._stream_openai(prompt, system_prompt, conversation_history, **kwargs):
                yield chunk
    
    # ============================================
    # Claude (Anthropic) Implementation
    # ============================================
    
    async def _generate_claude(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Claude"""
        
        messages = self._format_messages_claude(prompt, conversation_history)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_prompt if system_prompt else "You are a helpful hospital management assistant.",
                messages=messages
            )
            
            return {
                "response": response.content[0].text,
                "provider": "anthropic",
                "model": self.model,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
    
    async def _stream_claude(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using Claude"""
        
        messages = self._format_messages_claude(prompt, conversation_history)
        
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_prompt if system_prompt else "You are a helpful hospital management assistant.",
                messages=messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        
        except Exception as e:
            raise Exception(f"Claude streaming error: {str(e)}")
    
    def _format_messages_claude(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict]]
    ) -> List[Dict]:
        """Format messages for Claude API"""
        
        messages = []
        
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    # ============================================
    # Gemini (Google) Implementation
    # ============================================
    
    async def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using Gemini"""
        
        try:
            # Build full prompt with system instructions
            full_prompt = ""
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\n"
            
            if conversation_history:
                for msg in conversation_history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    full_prompt += f"{role}: {msg['content']}\n\n"
            
            full_prompt += f"User: {prompt}\n\nAssistant:"
            
            # Generate response
            response = await asyncio.to_thread(
                self.client.generate_content,
                full_prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_output_tokens": kwargs.get("max_tokens", self.max_tokens),
                }
            )
            
            return {
                "response": response.text,
                "provider": "gemini",
                "model": self.model_name,
                "tokens_used": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def _stream_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using Gemini"""
        
        try:
            # Build full prompt
            full_prompt = ""
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\n"
            
            if conversation_history:
                for msg in conversation_history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    full_prompt += f"{role}: {msg['content']}\n\n"
            
            full_prompt += f"User: {prompt}\n\nAssistant:"
            
            # Stream response
            response = await asyncio.to_thread(
                self.client.generate_content,
                full_prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_output_tokens": kwargs.get("max_tokens", self.max_tokens),
                },
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        except Exception as e:
            raise Exception(f"Gemini streaming error: {str(e)}")
    
    # ============================================
    # OpenAI Implementation
    # ============================================
    
    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        
        messages = self._format_messages_openai(prompt, system_prompt, conversation_history)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            return {
                "response": response.choices[0].message.content,
                "provider": "openai",
                "model": self.model,
                "tokens_used": response.usage.total_tokens,
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def _stream_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using OpenAI"""
        
        messages = self._format_messages_openai(prompt, system_prompt, conversation_history)
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {str(e)}")
    
    def _format_messages_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        conversation_history: Optional[List[Dict]]
    ) -> List[Dict]:
        """Format messages for OpenAI API"""
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    # ============================================
    # Specialized Methods for Hospital Agent
    # ============================================
    
    async def generate_prediction_analysis(
        self,
        hospital_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        historical_patterns: List[Dict],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate hospital admission prediction with detailed reasoning
        """
        
        system_prompt = """You are an expert hospital operations analyst. 
Analyze data and provide detailed admission forecasts with actionable recommendations.
Always respond with valid JSON."""
        
        prompt = f"""Analyze the following hospital data and generate a prediction:

## Current Hospital Status
{json.dumps(hospital_data, indent=2)}

## Weather Forecast
{json.dumps(weather_data, indent=2)}

## Historical Patterns (Last 7 Days)
{json.dumps(historical_patterns, indent=2)}

## Additional Context
{additional_context or 'None'}

Provide your analysis in JSON format:
{{
  "predicted_admissions": <number>,
  "confidence": <0.0-1.0>,
  "key_factors": ["factor1", "factor2", "factor3"],
  "risk_level": "low|medium|high",
  "recommendations": ["rec1", "rec2", "rec3"],
  "reasoning": "detailed explanation",
  "department_predictions": {{
    "emergency": <number>,
    "icu": <number>,
    "general": <number>
  }}
}}"""
        
        response = await self.generate_response(prompt, system_prompt)
        
        # Parse JSON from response
        try:
            response_text = response["response"]
            
            # Clean markdown if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            response_text = response_text.strip()
            result = json.loads(response_text)
            
            # Add metadata
            result["llm_provider"] = self.provider
            result["model"] = self.model if hasattr(self, 'model') else self.model_name
            result["tokens_used"] = response.get("tokens_used")
            
            return result
        
        except json.JSONDecodeError as e:
            # Fallback prediction
            return {
                "predicted_admissions": hospital_data.get("current_admissions", 100),
                "confidence": 0.5,
                "key_factors": ["Unable to parse LLM response"],
                "risk_level": "medium",
                "recommendations": ["Manual review needed"],
                "reasoning": f"JSON parsing error: {str(e)}",
                "error": True,
                "raw_response": response_text
            }
    
    async def generate_chat_response(
        self,
        user_message: str,
        conversation_history: List[Dict],
        hospital_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a conversational response with hospital context
        """
        
        system_prompt = """You are a helpful hospital management AI assistant.
You help hospital staff with:
- Answering questions about hospital operations
- Providing predictions and insights
- Explaining medical protocols
- Assisting with scheduling and resource allocation

Be professional, accurate, and concise."""
        
        # Add hospital context to prompt if available
        if hospital_context:
            context_str = f"\n\nCurrent Hospital Status:\n{json.dumps(hospital_context, indent=2)}"
            user_message = user_message + context_str
        
        return await self.generate_response(
            user_message,
            system_prompt,
            conversation_history
        )


# Singleton instance
_llm_service_instance = None

def get_llm_service() -> LLMService:
    """Get or create LLM service singleton"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance