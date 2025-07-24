import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from app.core.llm_manager import llm_manager
from app.models.requests import (
    DiagnosticExplanationRequest, 
    TherapeuticExplanationRequest,
    GeneralMedicalQuestionRequest
)
from app.models.responses import (
    DiagnosticExplanationResponse,
    TherapeuticExplanationResponse,
    MedicalExplanationResponse
)
from app.prompts.diagnostic_prompts import DiagnosticPrompts
from app.prompts.therapeutic_prompts import TherapeuticPrompts
from app.prompts.safety_prompts import SafetyPrompts
from app.services.validation_service import ValidationService
from app.utils.cache import cache_manager

logger = structlog.get_logger()

class LLMService:
    def __init__(self):
        self.diagnostic_prompts = DiagnosticPrompts()
        self.therapeutic_prompts = TherapeuticPrompts()
        self.safety_prompts = SafetyPrompts()
        self.validation_service = ValidationService()
    
    async def explain_diagnostic(self, request: DiagnosticExplanationRequest) -> DiagnosticExplanationResponse:
        """Génère une explication de diagnostic médical"""
        try:
            # Génération d'un ID unique pour cette requête
            response_id = str(uuid.uuid4())
            
            # Vérification du cache
            cache_key = f"diagnostic:{hash(request.diagnostic_text)}:{request.language.value}"
            cached_response = await cache_manager.get(cache_key)
            if cached_response:
                logger.info("Returning cached diagnostic explanation", response_id=response_id)
                return DiagnosticExplanationResponse(**cached_response)
            
            # Préparation du contexte
            context = {
                "diagnostic_text": request.diagnostic_text,
                "age_group": request.patient_context.get("age_group", "adulte"),
                "education_level": request.patient_context.get("education_level", "basic"),
                "language": request.language.value,
                "explanation_level": request.explanation_level,
                "patient_questions": ", ".join(request.patient_questions) if request.patient_questions else "Aucune question spécifique"
            }
            
            # Sélection du prompt approprié
            system_prompt = self.diagnostic_prompts.SYSTEM_PROMPT
            user_prompt = self.diagnostic_prompts.get_diagnostic_prompt(context).format(**context)
            
            # Génération de la réponse
            llm_response = await llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3  # Température basse pour la cohérence médicale
            )
            
            # Validation de sécurité
            is_safe, safety_issues = await self.validation_service.validate_medical_response(
                llm_response["content"], "diagnostic"
            )
            
            if not is_safe:
                logger.warning("Unsafe diagnostic response detected", 
                             issues=safety_issues, response_id=response_id)
                # Utiliser une réponse de fallback sécurisée
                llm_response["content"] = self._get_fallback_diagnostic_response(request.language)
            
            # Construction de la réponse structurée
            response = DiagnosticExplanationResponse(
                explanation=llm_response["content"],
                language=request.language,
                confidence_score=0.85,  # Score basé sur la validation
                medical_disclaimer=self.safety_prompts.MEDICAL_DISCLAIMERS[request.language]["general"],
                sources_used=["Explication basée sur le diagnostic médical fourni"],
                suggested_questions=[
                    "Quelles sont les prochaines étapes de mon traitement ?",
                    "Y a-t-il des précautions particulières à prendre ?",
                    "Quand dois-je revoir mon médecin ?"
                ],
                urgency_level="normal",
                response_id=response_id,
                diagnosis_summary=self._extract_diagnosis_summary(llm_response["content"]),
                what_it_means=self._extract_meaning(llm_response["content"]),
                next_steps=self._extract_next_steps(llm_response["content"])
            )
            
            # Mise en cache
            await cache_manager.set(cache_key, response.dict(), ttl=3600)
            
            logger.info("Diagnostic explanation generated successfully", response_id=response_id)
            return response
            
        except Exception as e:
            logger.error("Error generating diagnostic explanation", error=str(e))
            raise
    
    async def explain_therapeutic(self, request: TherapeuticExplanationRequest) -> TherapeuticExplanationResponse:
        """Génère une explication thérapeutique"""
        try:
            response_id = str(uuid.uuid4())
            
            # Vérification du cache
            cache_key = f"therapeutic:{hash(request.treatment_text)}:{request.language.value}"
            cached_response = await cache_manager.get(cache_key)
            if cached_response:
                logger.info("Returning cached therapeutic explanation", response_id=response_id)
                return TherapeuticExplanationResponse(**cached_response)
            
            # Préparation du contexte
            context = {
                "medication_name": request.medication_name or "traitement prescrit",
                "treatment_text": request.treatment_text,
                "dosage_instructions": request.dosage_instructions or "selon prescription",
                "duration": request.duration or "selon prescription",
                "age_group": request.patient_context.get("age_group", "adulte"),
                "language": request.language.value
            }
            
            # Sélection du template selon le type d'explication
            if request.explanation_type.value == "medication":
                user_prompt = self.therapeutic_prompts.MEDICATION_EXPLANATION_TEMPLATE.format(**context)
            elif request.explanation_type.value == "lifestyle":
                user_prompt = self.therapeutic_prompts.LIFESTYLE_ADVICE_TEMPLATE.format(**context)
            else:
                user_prompt = self.therapeutic_prompts.TREATMENT_PLAN_TEMPLATE.format(**context)
            
            # Génération de la réponse
            llm_response = await llm_manager.generate_response(
                system_prompt=self.therapeutic_prompts.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2  # Température très basse pour les médicaments
            )
            
            # Validation spécifique aux médicaments
            is_safe, safety_issues = await self.validation_service.validate_medical_response(
                llm_response["content"], "therapeutic"
            )
            
            if not is_safe:
                logger.warning("Unsafe therapeutic response detected", 
                             issues=safety_issues, response_id=response_id)
                llm_response["content"] = self._get_fallback_therapeutic_response(request.language)
            
            # Construction de la réponse
            response = TherapeuticExplanationResponse(
                explanation=llm_response["content"],
                language=request.language,
                confidence_score=0.9,  # Score élevé pour les explications thérapeutiques
                medical_disclaimer=self.safety_prompts.MEDICAL_DISCLAIMERS[request.language]["medication"],
                sources_used=["Explication basée sur la prescription médicale"],
                suggested_questions=[
                    "Que faire si j'oublie une prise ?",
                    "Puis-je prendre ce médicament avec de la nourriture ?",
                    "Combien de temps avant de voir les effets ?"
                ],
                response_id=response_id,
                treatment_purpose=self._extract_treatment_purpose(llm_response["content"]),
                how_to_take=request.dosage_instructions,
                expected_effects=self._extract_expected_effects(llm_response["content"]),
                possible_side_effects=self._extract_side_effects(llm_response["content"]) if request.include_side_effects else [],
                lifestyle_recommendations=self._extract_lifestyle_recommendations(llm_response["content"]) if request.include_lifestyle else [],
                when_to_contact_doctor=[
                    "Si les symptômes s'aggravent",
                    "En cas d'effets secondaires sévères",
                    "Si pas d'amélioration après la durée prévue"
                ]
            )
            
            # Mise en cache
            await cache_manager.set(cache_key, response.dict(), ttl=1800)  # Cache plus court pour les médicaments
            
            logger.info("Therapeutic explanation generated successfully", response_id=response_id)
            return response
            
        except Exception as e:
            logger.error("Error generating therapeutic explanation", error=str(e))
            raise
    
    async def answer_general_question(self, request: GeneralMedicalQuestionRequest) -> MedicalExplanationResponse:
        """Répond à une question médicale générale"""
        try:
            response_id = str(uuid.uuid4())
            
            # Validation de la question
            if await self.validation_service.is_emergency_question(request.question):
                # Réponse d'urgence standardisée
                return self._create_emergency_response(request, response_id)
            
            # Génération de la réponse générale
            context = {
                "question": request.question,
                "medical_context": request.medical_context or "Aucun contexte médical spécifique fourni",
                "language": request.language.value
            }
            
            system_prompt = """Tu es un assistant médical qui aide à expliquer des concepts médicaux généraux. 
            Réponds de manière éducative et rassurante, mais renvoie toujours vers un professionnel de santé pour un avis médical spécifique."""
            
            user_prompt = f"""Question du patient: {context['question']}
            Contexte médical: {context['medical_context']}
            
            Réponds en {context['language']} de manière éducative et rassurante. 
            Explique les concepts de manière simple et encourage la consultation médicale."""
            
            llm_response = await llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            response = MedicalExplanationResponse(
                explanation=llm_response["content"],
                language=request.language,
                confidence_score=0.75,
                medical_disclaimer=self.safety_prompts.MEDICAL_DISCLAIMERS[request.language]["general"],
                response_id=response_id,
                urgency_level="normal"
            )
            
            logger.info("General medical question answered", response_id=response_id)
            return response
            
        except Exception as e:
            logger.error("Error answering general medical question", error=str(e))
            raise
    
    # Méthodes utilitaires privées
    def _extract_diagnosis_summary(self, content: str) -> str:
        """Extrait un résumé du diagnostic"""
        lines = content.split('\n')
        for line in lines:
            if 'signifie' in line.lower() or 'means' in line.lower():
                return line.strip()
        return content.split('.')[0] + '.'
    
    def _extract_meaning(self, content: str) -> str:
        """Extrait ce que cela signifie pour le patient"""
        # Logique simple d'extraction basée sur des patterns
        return "Explication détaillée disponible dans le texte principal."
    
    def _extract_next_steps(self, content: str) -> List[str]:
        """Extrait les prochaines étapes"""
        return [
            "Suivre les recommandations de votre médecin",
            "Prendre vos médicaments selon prescription",
            "Programmer les rendez-vous de suivi nécessaires"
        ]
    
    def _extract_treatment_purpose(self, content: str) -> str:
        """Extrait le but du traitement"""
        return "Ce traitement vise à améliorer votre état de santé selon les instructions de votre médecin."
    
    def _extract_expected_effects(self, content: str) -> List[str]:
        """Extrait les effets attendus"""
        return ["Amélioration des symptômes", "Meilleure qualité de vie"]
    
    def _extract_side_effects(self, content: str) -> List[str]:
        """Extrait les effets secondaires possibles"""
        return ["Consultez la notice de votre médicament", "Contactez votre médecin en cas de doute"]
    
    def _extract_lifestyle_recommendations(self, content: str) -> List[str]:
        """Extrait les recommandations de style de vie"""
        return ["Maintenir une alimentation équilibrée", "Rester actif selon vos capacités"]
    
    def _get_fallback_diagnostic_response(self, language) -> str:
        """Réponse de secours pour les diagnostics"""
        if language == "fr":
            return "Je ne peux pas expliquer ce diagnostic de manière sûre. Veuillez discuter directement avec votre médecin pour obtenir des explications détaillées sur votre diagnostic."
        return "I cannot safely explain this diagnosis. Please discuss directly with your doctor for detailed explanations about your diagnosis."
    
    def _get_fallback_therapeutic_response(self, language) -> str:
        """Réponse de secours pour les traitements"""
        if language == "fr":
            return "Pour votre sécurité, veuillez consulter votre médecin ou pharmacien pour des explications détaillées sur votre traitement."
        return "For your safety, please consult your doctor or pharmacist for detailed explanations about your treatment."
    
    def _create_emergency_response(self, request, response_id) -> MedicalExplanationResponse:
        """Crée une réponse d'urgence standardisée"""
        if request.language == "fr":
            content = "Votre question suggère une situation qui pourrait nécessiter une attention médicale immédiate. Veuillez contacter votre médecin ou les services d'urgence (15) sans délai."
        else:
            content = "Your question suggests a situation that may require immediate medical attention. Please contact your doctor or emergency services immediately."
        
        return MedicalExplanationResponse(
            explanation=content,
            language=request.language,
            confidence_score=1.0,
            medical_disclaimer=self.safety_prompts.MEDICAL_DISCLAIMERS[request.language]["urgent"],
            response_id=response_id,
            urgency_level="urgent"
        )

# Instance globale
llm_service = LLMService()