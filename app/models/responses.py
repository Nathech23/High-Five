from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MedicalExplanationResponse(BaseModel):
    explanation: str = Field(..., description="Explication médicale en langage simple")
    language: Language = Field(..., description="Langue de la réponse")
    confidence_score: float = Field(..., ge=0.0, le=1.0, 
                                   description="Score de confiance de la réponse")
    medical_disclaimer: str = Field(..., description="Avertissement médical obligatoire")
    sources_used: Optional[List[str]] = Field(default=[], 
                                             description="Sources utilisées pour la réponse")
    suggested_questions: Optional[List[str]] = Field(default=[],
                                                    description="Questions suggérées au patient")
    urgency_level: str = Field(default="normal", 
                              description="Niveau d'urgence: normal, attention, urgent")
    generated_at: datetime = Field(default_factory=datetime.now)
    response_id: str = Field(..., description="Identifiant unique de la réponse")

class DiagnosticExplanationResponse(MedicalExplanationResponse):
    diagnosis_summary: str = Field(..., description="Résumé du diagnostic en mots simples")
    what_it_means: str = Field(..., description="Ce que cela signifie pour le patient")
    next_steps: Optional[List[str]] = Field(default=[], 
                                           description="Prochaines étapes recommandées")
    lifestyle_impact: Optional[str] = Field(default=None,
                                           description="Impact sur le style de vie")

class TherapeuticExplanationResponse(MedicalExplanationResponse):
    treatment_purpose: str = Field(..., description="Pourquoi ce traitement")
    how_to_take: Optional[str] = Field(default=None, 
                                      description="Comment prendre le médicament")
    expected_effects: Optional[List[str]] = Field(default=[],
                                                 description="Effets attendus")
    possible_side_effects: Optional[List[str]] = Field(default=[],
                                                      description="Effets secondaires possibles")
    lifestyle_recommendations: Optional[List[str]] = Field(default=[],
                                                          description="Recommandations de style de vie")
    when_to_contact_doctor: Optional[List[str]] = Field(default=[],
                                                       description="Quand contacter le médecin")

class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Statut du service")
    timestamp: datetime = Field(default_factory=datetime.now)
    llm_model: str = Field(..., description="Modèle LLM utilisé")
    model_available: bool = Field(..., description="Disponibilité du modèle")
    cache_status: str = Field(..., description="Statut du cache Redis")
    version: str = Field(default="1.0.0", description="Version du service")