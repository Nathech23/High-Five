from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import logging

from ..database.models import Patient, Department, Feedback
from ..schemas.patient import PatientCreate, PatientUpdate, PatientSummary

logger = logging.getLogger(__name__)

class PatientService:
    """Service class for patient operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_patients(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Patient]:
        """Get patients with optional filtering"""
        query = self.db.query(Patient)
        
        if filters:
            if 'department_id' in filters:
                query = query.filter(Patient.department_id == filters['department_id'])
            if 'preferred_language' in filters:
                query = query.filter(Patient.preferred_language == filters['preferred_language'])
        
        return query.offset(skip).limit(limit).all()
    
    def get_patients_summary(self, skip: int = 0, limit: int = 100) -> List[PatientSummary]:
        """Get patients with feedback statistics"""
        query = self.db.query(
            Patient.id,
            Patient.first_name,
            Patient.last_name,
            Patient.preferred_language,
            Patient.department_id,
            func.count(Feedback.id).label('total_feedbacks'),
            func.avg(Feedback.rating).label('avg_rating')
        ).outerjoin(Feedback).group_by(Patient.id)
        
        results = query.offset(skip).limit(limit).all()
        
        summaries = []
        for result in results:
            summaries.append(PatientSummary(
                id=result.id,
                first_name=result.first_name,
                last_name=result.last_name,
                preferred_language=result.preferred_language,
                department_id=result.department_id,
                total_feedbacks=result.total_feedbacks or 0,
                avg_rating=float(result.avg_rating) if result.avg_rating else None
            ))
        
        return summaries
    
    def get_patient(self, patient_id: int) -> Optional[Patient]:
        """Get patient by ID"""
        return self.db.query(Patient).filter(Patient.id == patient_id).first()
    
    def create_patient(self, patient_data: PatientCreate) -> Patient:
        """Create new patient"""
        db_patient = Patient(**patient_data.model_dump())
        self.db.add(db_patient)
        self.db.commit()
        self.db.refresh(db_patient)
        
        logger.info(f"Created patient: {db_patient.first_name} {db_patient.last_name}")
        return db_patient
    
    def update_patient(self, patient_id: int, patient_data: PatientUpdate) -> Patient:
        """Update patient"""
        db_patient = self.get_patient(patient_id)
        if not db_patient:
            raise ValueError("Patient not found")
        
        update_data = patient_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_patient, field, value)
        
        self.db.commit()
        self.db.refresh(db_patient)
        
        logger.info(f"Updated patient {patient_id}")
        return db_patient
    
    def delete_patient(self, patient_id: int) -> bool:
        """Delete patient"""
        db_patient = self.get_patient(patient_id)
        if not db_patient:
            return False
        
        self.db.delete(db_patient)
        self.db.commit()
        
        logger.info(f"Deleted patient {patient_id}")
        return True
    
    def department_exists(self, department_id: int) -> bool:
        """Check if department exists"""
        return self.db.query(Department).filter(Department.id == department_id).first() is not None
    
    def patient_has_feedbacks(self, patient_id: int) -> bool:
        """Check if patient has any feedbacks"""
        count = self.db.query(Feedback).filter(Feedback.patient_id == patient_id).count()
        return count > 0
    
    def get_patient_feedbacks(self, patient_id: int, skip: int = 0, limit: int = 50) -> List[Feedback]:
        """Get feedbacks for a specific patient"""
        return self.db.query(Feedback).filter(
            Feedback.patient_id == patient_id
        ).order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()
    
    def search_patients(self, search_term: str, limit: int = 20) -> List[Patient]:
        """Search patients by name or email"""
        search_pattern = f"%{search_term}%"
        
        return self.db.query(Patient).filter(
            (Patient.first_name.ilike(search_pattern)) |
            (Patient.last_name.ilike(search_pattern)) |
            (Patient.email.ilike(search_pattern))
        ).limit(limit).all()
    
    def get_patients_by_department(self, department_id: int) -> List[Patient]:
        """Get all patients in a specific department"""
        return self.db.query(Patient).filter(Patient.department_id == department_id).all()
    
    def get_patients_by_language(self, language: str) -> List[Patient]:
        """Get patients by preferred language"""
        return self.db.query(Patient).filter(Patient.preferred_language == language).all()
    
    def count_patients(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total patients with optional filters"""
        query = self.db.query(Patient)
        
        if filters:
            if 'department_id' in filters:
                query = query.filter(Patient.department_id == filters['department_id'])
            if 'preferred_language' in filters:
                query = query.filter(Patient.preferred_language == filters['preferred_language'])
        
        return query.count()