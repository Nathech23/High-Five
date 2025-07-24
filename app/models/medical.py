from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum

class MedicalDomain(str, Enum):
    CARDIOLOGY = "cardiologie"
    NEUROLOGY = "neurologie"
    PEDIATRICS = "pediatrie"
    GENERAL = "general"
    EMERGENCY = "urgence"
    CHRONIC = "chronique"

class PatientProfile(BaseModel):
    age_group: Optional[str] = Field(default=None, description="Tranche d'âge")
    education_level: Optional[str] = Field(default="basic", description="Niveau d'éducation")
    language_preference: Language = Field(default=Language.FRENCH)
    cultural_context: Optional[str] = Field(default=None)
    medical_literacy: str = Field(default="basic", description="Littératie médicale")

class MedicalValidationCriteria(BaseModel):
    contains_medical_advice: bool = Field(default=False)
    safety_level: str = Field(default="safe", description="safe, caution, warning")
    requires_medical_attention: bool = Field(default=False)
    contains_drug_interactions: bool = Field(default=False)
    emergency_keywords: List[str] = Field(default=[])
