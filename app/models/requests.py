from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum

class Language(str, Enum):
    FRENCH = "fr"
    ENGLISH = "en"
    DOUALA = "douala"
    BASSA = "bassa"
    EWONDO = "ewondo"

class ExplanationType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    TREATMENT = "treatment"
    MEDICATION = "medication"
    LIFESTYLE = "lifestyle"
    FOLLOWUP = "followup"

class DiagnosticExplanationRequest(BaseModel):
    diagnostic_text: str = Field(..., min_length=10, max_length=2000, 
                                description="Texte du diagnostic du médecin")
    patient_context: Optional[Dict[str, Any]] = Field(default={}, 
                                                     description="Contexte patient (âge, niveau éducation, etc.)")
    language: Language = Field(default=Language.FRENCH, 
                              description="Langue de réponse souhaitée")
    explanation_level: str = Field(default="simple", 
                                  description="Niveau d'explication: simple, detaille, technique")
    patient_questions: Optional[List[str]] = Field(default=[], 
                                                  description="Questions spécifiques du patient")
    
    @validator('diagnostic_text')
    def validate_diagnostic_text(cls, v):
        if not v or v.isspace():
            raise ValueError("Le texte du diagnostic ne peut pas être vide")
        return v.strip()

class TherapeuticExplanationRequest(BaseModel):
    treatment_text: str = Field(..., min_length=5, max_length=2000,
                               description="Texte du traitement/médicament prescrit")
    medication_name: Optional[str] = Field(default=None,
                                          description="Nom du médicament si applicable")
    dosage_instructions: Optional[str] = Field(default=None,
                                              description="Instructions de dosage")
    duration: Optional[str] = Field(default=None,
                                   description="Durée du traitement")
    patient_context: Optional[Dict[str, Any]] = Field(default={},
                                                     description="Contexte patient")
    language: Language = Field(default=Language.FRENCH)
    explanation_type: ExplanationType = Field(default=ExplanationType.TREATMENT)
    include_side_effects: bool = Field(default=True,
                                      description="Inclure les effets secondaires")
    include_lifestyle: bool = Field(default=True,
                                   description="Inclure recommandations lifestyle")

class GeneralMedicalQuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000,
                         description="Question médicale du patient")
    medical_context: Optional[str] = Field(default=None,
                                          description="Contexte médical fourni par le médecin")
    language: Language = Field(default=Language.FRENCH)
    patient_context: Optional[Dict[str, Any]] = Field(default={})
