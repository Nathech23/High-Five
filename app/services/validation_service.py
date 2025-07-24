import re
from typing import Tuple, List, Dict, Any
import structlog
from app.prompts.safety_prompts import SafetyPrompts

logger = structlog.get_logger()

class ValidationService:
    def __init__(self):
        self.safety_prompts = SafetyPrompts()
        self.red_flags = self.safety_prompts.RED_FLAG_KEYWORDS
        
        # Patterns dangereux
        self.dangerous_patterns = [
            r"arrêtez?\s+(?:de|le)\s+\w+",  # "arrêtez de prendre", "arrêtez le traitement"
            r"ne\s+prenez\s+pas",           # "ne prenez pas"
            r"remplacez?\s+par",            # "remplacez par"
            r"vous\s+avez\s+(?:un|une)",    # diagnostic direct
            r"je\s+vous\s+prescris",        # prescription
            r"stop\s+taking",               # anglais
            r"don't\s+take",                # anglais
        ]
        
        # Mots-clés d'urgence
        self.emergency_keywords = [
            "urgence", "emergency", "douleur intense", "severe pain",
            "difficulté à respirer", "difficulty breathing", "chest pain",
            "douleur thoracique", "évanouissement", "fainting", "suicide",
            "overdose", "surdose", "bleeding", "saignement"
        ]
        
        # Médicaments nécessitant attention particulière
        self.high_risk_medications = [
            "warfarine", "warfarin", "anticoagulant", "insuline", "insulin",
            "digitaline", "digoxin", "lithium", "méthotrexate", "methotrexate"
        ]
    
    async def validate_medical_response(self, response: str, response_type: str) -> Tuple[bool, List[str]]:
        """Valide une réponse médicale pour s'assurer qu'elle est sûre"""
        issues = []
        
        # Vérification des patterns dangereux
        for pattern in self.dangerous_patterns:
            if re.search(pattern, response.lower(), re.IGNORECASE):
                issues.append(f"Pattern dangereux détecté: {pattern}")
        
        # Vérification des mots-clés rouges
        for red_flag in self.red_flags:
            if red_flag.lower() in response.lower():
                issues.append(f"Mot-clé rouge détecté: {red_flag}")
        
        # Validations spécifiques par type
        if response_type == "therapeutic":
            therapeutic_issues = await self._validate_therapeutic_response(response)
            issues.extend(therapeutic_issues)
        elif response_type == "diagnostic":
            diagnostic_issues = await self._validate_diagnostic_response(response)
            issues.extend(diagnostic_issues)
        
        # Vérification de la présence d'avertissements
        if not self._has_medical_disclaimer(response):
            issues.append("Avertissement médical manquant")
        
        is_safe = len(issues) == 0
        
        if not is_safe:
            logger.warning("Unsafe medical response detected", 
                         response_type=response_type, issues=issues)
        
        return is_safe, issues
    
    async def _validate_therapeutic_response(self, response: str) -> List[str]:
        """Validations spécifiques aux réponses thérapeutiques"""
        issues = []
        
        # Vérification des modifications de dosage
        dosage_modification_patterns = [
            r"augmentez?\s+(?:la\s+)?dose",
            r"diminuez?\s+(?:la\s+)?dose",
            r"prenez\s+\d+\s+fois\s+plus",
            r"take\s+more",
            r"take\s+less"
        ]
        
        for pattern in dosage_modification_patterns:
            if re.search(pattern, response.lower()):
                issues.append(f"Modification de dosage détectée: {pattern}")
        
        # Vérification des interactions médicamenteuses non appropriées
        if "mélangez avec" in response.lower() or "combine with" in response.lower():
            issues.append("Possible conseil d'interaction médicamenteuse")
        
        return issues
    
    async def _validate_diagnostic_response(self, response: str) -> List[str]:
        """Validations spécifiques aux réponses diagnostiques"""
        issues = []
        
        # Vérification des diagnostics directs
        diagnostic_patterns = [
            r"vous\s+avez\s+(?:un|une|du|de\s+la)",
            r"votre\s+diagnostic\s+est",
            r"you\s+have\s+(?:a|an)",
            r"your\s+diagnosis\s+is"
        ]
        
        for pattern in diagnostic_patterns:
            if re.search(pattern, response.lower()):
                issues.append(f"Diagnostic direct détecté: {pattern}")
        
        return issues
    
    async def is_emergency_question(self, question: str) -> bool:
        """Détermine si une question indique une urgence médicale"""
        question_lower = question.lower()
        
        return any(keyword in question_lower for keyword in self.emergency_keywords)
    
    def _has_medical_disclaimer(self, response: str) -> bool:
        """Vérifie si la réponse contient un avertissement médical"""
        disclaimer_indicators = [
            "important:", "⚠️", "avertissement", "warning", 
            "consultez votre médecin", "consult your doctor",
            "ne remplace pas", "does not replace"
        ]
        
        return any(indicator in response.lower() for indicator in disclaimer_indicators)
    
    async def check_medication_interactions(self, medications: List[str]) -> Dict[str, Any]:
        """Vérifie les interactions potentielles entre médicaments"""
        # Cette méthode pourrait être étendue avec une base de données d'interactions
        high_risk_detected = []
        
        for med in medications:
            if any(risk_med in med.lower() for risk_med in self.high_risk_medications):
                high_risk_detected.append(med)
        
        return {
            "has_high_risk": len(high_risk_detected) > 0,
            "high_risk_medications": high_risk_detected,
            "recommendation": "Consultez votre pharmacien ou médecin" if high_risk_detected else "Aucun risque élevé détecté"
        }