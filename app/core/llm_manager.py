import ollama
import asyncio
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from app.core.config import settings

logger = structlog.get_logger()

class LLMManager:
    def __init__(self):
        self.client = None
        self.model_name = settings.llm_model
        self.base_url = settings.ollama_base_url
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.context_window = settings.llm_context_window
        
    async def initialize(self):
        """Initialise la connexion avec Ollama"""
        try:
            self.client = ollama.AsyncClient(host=self.base_url)
            await self._check_model_availability()
            logger.info("LLM Manager initialized successfully", model=self.model_name)
        except Exception as e:
            logger.error("Failed to initialize LLM Manager", error=str(e))
            raise
    
    async def _check_model_availability(self):
        """Vérifie si le modèle est disponible"""
        try:
            models = await self.client.list()
            available_models = [model['name'] for model in models['models']]
            
            if self.model_name not in available_models:
                logger.warning(f"Model {self.model_name} not found, pulling it...")
                await self.client.pull(self.model_name)
                logger.info(f"Model {self.model_name} pulled successfully")
            
        except Exception as e:
            logger.error("Error checking model availability", error=str(e))
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, 
                              system_prompt: str, 
                              user_prompt: str,
                              **kwargs) -> Dict[str, Any]:
        """Génère une réponse avec le LLM"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat(
                model=self.model_name,
                messages=messages,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens),
                    "num_ctx": self.context_window
                }
            )
            
            return {
                "content": response['message']['content'],
                "model": self.model_name,
                "tokens_used": response.get('eval_count', 0),
                "generation_time": response.get('total_duration', 0) / 1e9  # Convert to seconds
            }
            
        except Exception as e:
            logger.error("Error generating LLM response", error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé du service LLM"""
        try:
            # Test simple pour vérifier la connectivité
            test_response = await self.generate_response(
                system_prompt="Tu es un assistant médical.",
                user_prompt="Dis juste 'OK' pour confirmer que tu fonctionnes."
            )
            
            return {
                "status": "healthy",
                "model": self.model_name,
                "response_time": test_response.get("generation_time", 0),
                "available": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.model_name,
                "error": str(e),
                "available": False
            }

# Instance globale
llm_manager = LLMManager()