"""Service for interacting with Google Gemini API for WellMom AI Chatbot."""

import asyncio
import logging
from typing import List, Optional, Tuple, Dict, Any

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import settings

logger = logging.getLogger(__name__)


class ChatbotService:
    """Service for interacting with Gemini API with token management."""
    
    SYSTEM_PROMPT = """
    Kamu adalah WellMom Assistant, asisten kesehatan maternal yang ramah dan informatif.
    
    ## Identitas
    - Nama: WellMom Assistant
    - Peran: Asisten kesehatan untuk ibu hamil
    - Bahasa: Bahasa Indonesia yang sopan dan mudah dipahami
    
    ## Tugas Utama
    - Menjawab pertanyaan seputar kehamilan: gejala, nutrisi, olahraga, tanda bahaya
    - Memberikan informasi kesehatan yang akurat dan mudah dipahami
    - Memberikan dukungan emosional dengan empati
    - Mengingatkan untuk selalu berkonsultasi dengan bidan/dokter untuk masalah serius
    
    ## Batasan Penting
    - JANGAN memberikan diagnosis medis
    - JANGAN merekomendasikan obat-obatan tanpa saran dokter
    - JANGAN menjawab pertanyaan di luar topik kesehatan kehamilan
    - Untuk pertanyaan di luar topik, tolak dengan sopan dan arahkan kembali ke topik kehamilan
    
    ## Gaya Komunikasi
    - Gunakan bahasa yang hangat dan mendukung
    - Panggil pengguna dengan "Ibu" atau "Bunda"
    - Berikan jawaban yang ringkas namun informatif
    - Sertakan emoji yang relevan untuk membuat percakapan lebih ramah 🤰💕
    
    ## Format Respons
    - Untuk pertanyaan kesehatan: berikan informasi + saran + reminder konsultasi dokter
    - Untuk keluhan: tunjukkan empati + informasi + kapan harus ke dokter
    - Untuk pertanyaan umum kehamilan: jawab informatif + tips praktis
    """
    
    def __init__(self):
        """Initialize Gemini API client."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tidak ditemukan di environment variables")
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # First, try to get available models from API
            available_model_names = []
            try:
                models = genai.list_models()
                for model in models:
                    # Only include models that support generateContent
                    if 'generateContent' in model.supported_generation_methods:
                        model_name = model.name.replace('models/', '')
                        available_model_names.append(model_name)
                logger.info(f"Found {len(available_model_names)} available models from API")
            except Exception as e:
                logger.warning(f"Could not list models from API: {str(e)}, using fallback list")
                available_model_names = []
            
            # Preferred model names in order of preference
            # Updated to match available models (gemini-2.0, gemini-2.5, gemini-flash-latest, etc)
            preferred_models = [
                'gemini-flash-latest',        # Latest flash model (available)
                'gemini-2.0-flash',          # Gemini 2.0 flash
                'gemini-2.5-flash',          # Gemini 2.5 flash
                'gemini-pro-latest',         # Latest pro model (available)
                'gemini-2.5-pro',            # Gemini 2.5 pro
                # Legacy models (may not be available for all API keys)
                'gemini-1.5-flash-latest',
                'gemini-1.5-flash',
                'gemini-1.5-pro-latest',
                'gemini-1.5-pro',
                'gemini-pro',
            ]
            
            # If we have available models from API, use those directly
            if available_model_names:
                # Create ordered list: preferred models that are available, then other available models
                model_names = []
                
                # First, add preferred models that are in available list (exact match)
                for pref in preferred_models:
                    if pref in available_model_names:
                        model_names.append(pref)
                
                # Then, add preferred models that match by prefix (e.g., gemini-2.0-flash matches gemini-2.0-flash-001)
                for pref in preferred_models:
                    if pref not in model_names:
                        matching = [m for m in available_model_names if m.startswith(pref + '-') or pref.startswith(m.split('-')[0] + '-')]
                        if matching:
                            # Use the first match (usually the most specific version)
                            model_names.append(matching[0])
                
                # Finally, add other available models that weren't in preferred list
                for avail in available_model_names:
                    if avail not in model_names:
                        model_names.append(avail)
                
                logger.info(f"Using {len(model_names)} models in priority order (first: {model_names[0] if model_names else 'none'})")
            else:
                # Fallback to preferred models if we can't list from API
                model_names = preferred_models
                logger.warning("Using fallback model list (could not fetch from API)")
            
            self.model = None
            last_error = None
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(
                        model_name,
                        system_instruction=self.SYSTEM_PROMPT,
                        safety_settings={
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        }
                    )
                    # Model instance created successfully
                    logger.info(f"Successfully initialized Gemini model: {model_name}")
                    self.model_name = model_name
                    break
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # Log more specific error information
                    if "404" in error_str or "not found" in error_str:
                        logger.warning(f"Model {model_name} not found for this API key")
                    elif "api key" in error_str or "authentication" in error_str or "permission" in error_str:
                        logger.error(f"API key authentication failed: {str(e)}")
                        raise ValueError(
                            f"API key tidak valid atau tidak memiliki akses ke Gemini API. "
                            f"Pastikan GEMINI_API_KEY benar dan memiliki akses yang diperlukan."
                        )
                    else:
                        logger.warning(f"Failed to initialize model {model_name}: {str(e)}")
                    continue
            
            if self.model is None:
                error_msg = f"Tidak dapat menginisialisasi model Gemini. Semua model gagal."
                logger.error(error_msg)
                logger.error(f"Tried models: {model_names}")
                logger.error(f"Available models from API: {available_model_names if available_model_names else 'Could not fetch'}")
                raise ValueError(
                    f"Gagal menginisialisasi model AI. "
                    f"Pastikan API key valid dan memiliki akses ke Gemini API. "
                    f"Error terakhir: {str(last_error)}"
                )
                
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {str(e)}")
            raise ValueError(
                f"Gagal menginisialisasi Gemini API: {str(e)}. "
                f"Pastikan GEMINI_API_KEY valid dan terkonfigurasi dengan benar."
            )
    
    def _try_reinitialize_model(self):
        """Try to reinitialize with a different model if current one fails."""
        current_model = getattr(self, 'model_name', None)
        
        # Get available models from API
        available_model_names = []
        try:
            models = genai.list_models()
            for model in models:
                if 'generateContent' in model.supported_generation_methods:
                    model_name = model.name.replace('models/', '')
                    available_model_names.append(model_name)
        except Exception as e:
            logger.warning(f"Could not list models for reinitialize: {str(e)}")
        
        # Preferred models in order (updated to match available models)
        preferred_models = [
            'gemini-flash-latest',
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini-pro-latest',
            'gemini-2.5-pro',
            # Legacy models
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro-latest',
            'gemini-1.5-pro',
            'gemini-pro',
        ]
        
        # Build list of models to try
        if available_model_names:
            # Prioritize preferred models that are available
            model_names = []
            for pref in preferred_models:
                matching = [m for m in available_model_names if pref in m or m == pref]
                if matching and matching[0] != current_model:
                    model_names.append(matching[0])
            
            # Add other available models
            for avail in available_model_names:
                if avail != current_model and avail not in model_names:
                    model_names.append(avail)
        else:
            # Fallback: try all preferred models except current
            model_names = [m for m in preferred_models if m != current_model]
        
        # Try each model
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(
                    model_name,
                    system_instruction=self.SYSTEM_PROMPT,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    }
                )
                logger.info(f"Reinitialized with model: {model_name}")
                self.model_name = model_name
                return True
            except Exception as e:
                logger.warning(f"Failed to reinitialize with {model_name}: {str(e)}")
                continue
        
        return False
    
    async def chat(
        self,
        message: str,
        history: Optional[List[dict]] = None,
        timeout: Optional[int] = None
    ) -> Tuple[str, int, int]:
        """
        Send message to Gemini and get response.
        
        Args:
            message: User message to send
            history: Optional conversation history in format [{"role": "user", "parts": ["text"]}, ...]
            timeout: Request timeout in seconds (default: from settings)
        
        Returns:
            tuple: (response_text, input_tokens, output_tokens)
        
        Raises:
            TimeoutError: If request exceeds timeout
            ValueError: If API returns error
            Exception: For other API errors
        """
        if timeout is None:
            timeout = settings.CHATBOT_REQUEST_TIMEOUT
        
        try:
            # Prepare chat history
            if history is None:
                history = []
            
            # Start chat session
            chat = self.model.start_chat(history=history)
            
            # Send message with timeout
            try:
                # Use asyncio.to_thread to run synchronous Gemini API call in thread pool
                response = await asyncio.wait_for(
                    asyncio.to_thread(chat.send_message, message),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Gemini API request timeout after {timeout} seconds")
                raise TimeoutError(
                    f"Waktu respons habis setelah {timeout} detik. Silakan coba lagi."
                )
            except Exception as e:
                error_msg = str(e)
                # If model not found (404), try to reinitialize with different model
                if "404" in error_msg and ("not found" in error_msg.lower() or "not supported" in error_msg.lower()):
                    logger.warning(f"Model {self.model_name} not available, trying to reinitialize...")
                    retry_count = 0
                    max_retries = 5  # Try up to 5 different models
                    
                    while retry_count < max_retries:
                        if self._try_reinitialize_model():
                            # Retry with new model
                            logger.info(f"Retrying with model: {self.model_name}")
                            try:
                                chat = self.model.start_chat(history=history)
                                response = await asyncio.wait_for(
                                    asyncio.to_thread(chat.send_message, message),
                                    timeout=timeout
                                )
                                # Success! Break out of retry loop
                                break
                            except Exception as retry_error:
                                retry_error_msg = str(retry_error)
                                if "404" in retry_error_msg and ("not found" in retry_error_msg.lower() or "not supported" in retry_error_msg.lower()):
                                    # This model also doesn't work, try next one
                                    retry_count += 1
                                    logger.warning(f"Model {self.model_name} also not available, trying next model...")
                                    continue
                                else:
                                    # Different error, re-raise
                                    raise
                        else:
                            # No more models to try
                            break
                    
                    # If we exhausted all retries, raise original error
                    if retry_count >= max_retries or not self.model:
                        raise ValueError(
                            f"Tidak dapat menemukan model yang tersedia. "
                            f"Semua model yang dicoba tidak tersedia untuk API key ini. "
                            f"Silakan cek API key atau hubungi administrator."
                        )
                else:
                    # Re-raise to be handled in outer try-except
                    raise
            
            # Extract response text
            response_text = response.text
            
            # Get token usage from response
            # Note: Gemini API may not always provide token usage in free tier
            # We'll estimate if not available
            try:
                # Try to get usage metadata
                if hasattr(response, 'usage_metadata'):
                    input_tokens = response.usage_metadata.prompt_token_count or 0
                    output_tokens = response.usage_metadata.candidates_token_count or 0
                else:
                    # Fallback to estimation
                    input_tokens = self.count_tokens(message)
                    output_tokens = self.count_tokens(response_text)
            except Exception as e:
                logger.warning(f"Could not get token usage from response: {str(e)}")
                # Fallback to estimation
                input_tokens = self.count_tokens(message)
                output_tokens = self.count_tokens(response_text)
            
            logger.info(
                f"Chatbot response generated: {len(response_text)} chars, "
                f"{input_tokens} input tokens, {output_tokens} output tokens"
            )
            
            return (response_text, input_tokens, output_tokens)
            
        except TimeoutError:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini API error: {error_msg}")
            
            # Handle specific Gemini API errors
            if "404" in error_msg or "not found" in error_msg.lower():
                # Model not found - try to reinitialize with different model
                logger.error(f"Model not found error: {error_msg}")
                raise ValueError(
                    "Model AI tidak ditemukan. Silakan hubungi administrator untuk memperbarui konfigurasi."
                )
            elif "safety" in error_msg.lower() or "blocked" in error_msg.lower():
                raise ValueError(
                    "Pesan Anda tidak dapat diproses karena mengandung konten yang tidak sesuai. "
                    "Silakan coba dengan pertanyaan lain."
                )
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                raise ValueError(
                    "Layanan AI sedang sibuk. Silakan coba lagi dalam beberapa saat."
                )
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower() or "permission" in error_msg.lower():
                raise ValueError(
                    "Konfigurasi layanan AI tidak valid. Silakan hubungi administrator."
                )
            else:
                # Log full error for debugging
                logger.error(f"Gemini API error details: {error_msg}")
                raise ValueError(
                    f"Layanan AI sedang mengalami gangguan: {error_msg}. Silakan coba lagi."
                )
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Conservative estimation for Indonesian text:
        - 1 token ≈ 4 characters (more conservative than English)
        - This is a rough estimate, actual tokenization may vary
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Conservative estimate: 1 token per 4 characters for Indonesian
        # This accounts for Indonesian language characteristics
        estimated_tokens = len(text) // 4 + 1
        
        return estimated_tokens
    
    def format_history_for_gemini(
        self,
        messages: List[dict]
    ) -> List[dict]:
        """
        Format conversation history for Gemini API.
        
        Gemini expects history in format:
        [
            {"role": "user", "parts": ["text"]},
            {"role": "model", "parts": ["text"]},
            ...
        ]
        
        Args:
            messages: List of messages with 'role' and 'content' fields
        
        Returns:
            Formatted history for Gemini API
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Map 'assistant' to 'model' for Gemini
            if role == "assistant":
                role = "model"
            elif role not in ["user", "model"]:
                continue  # Skip invalid roles
            
            formatted.append({
                "role": role,
                "parts": [content]
            })
        
        return formatted
    
    def prepare_history_from_messages(
        self,
        messages: List[dict],
        max_messages: Optional[int] = None
    ) -> List[dict]:
        """
        Prepare conversation history from database messages.
        
        Args:
            messages: List of ChatbotMessage objects or dicts with role/content
            max_messages: Maximum number of messages to include (default: from settings)
        
        Returns:
            Formatted history for Gemini API
        """
        if max_messages is None:
            max_messages = settings.CHATBOT_MAX_HISTORY_MESSAGES
        
        # Convert messages to dict format if needed
        history = []
        for msg in messages[-max_messages:]:  # Take last N messages
            if isinstance(msg, dict):
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            else:
                # Assume it's a model object with role and content attributes
                history.append({
                    "role": getattr(msg, "role", "user"),
                    "content": getattr(msg, "content", "")
                })
        
        return self.format_history_for_gemini(history)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get service status information.
        
        Returns:
            dict: Status information including model_name, is_available, etc.
        """
        status = {
            "is_available": self.model is not None,
            "model_name": getattr(self, "model_name", None),
            "api_key_configured": bool(settings.GEMINI_API_KEY),
        }
        
        if self.model is None:
            status["error"] = "Model tidak terinisialisasi"
        else:
            status["error"] = None
        
        return status


# Singleton instance - lazy initialization
_chatbot_service_instance: Optional[ChatbotService] = None


def get_chatbot_service() -> ChatbotService:
    """Get or create chatbot service instance (lazy initialization)."""
    global _chatbot_service_instance
    if _chatbot_service_instance is None:
        try:
            _chatbot_service_instance = ChatbotService()
        except Exception as e:
            logger.error(f"Failed to initialize ChatbotService: {str(e)}")
            raise
    return _chatbot_service_instance


# For backward compatibility - property that uses lazy initialization
class _ChatbotServiceProxy:
    """Proxy class for backward compatibility."""
    
    def __init__(self):
        self._service: Optional[ChatbotService] = None
    
    def _get_service(self) -> ChatbotService:
        """Get service instance, with error handling."""
        if self._service is None:
            try:
                self._service = get_chatbot_service()
            except Exception as e:
                logger.error(f"Failed to get chatbot service: {str(e)}")
                raise ValueError(
                    f"Layanan AI tidak tersedia. "
                    f"Pastikan GEMINI_API_KEY sudah dikonfigurasi dengan benar. "
                    f"Error: {str(e)}"
                )
        return self._service
    
    def __getattr__(self, name):
        service = self._get_service()
        return getattr(service, name)

chatbot_service = _ChatbotServiceProxy()
