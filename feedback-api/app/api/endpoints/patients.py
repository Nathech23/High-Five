from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ...database.connection import get_db
from ...schemas.patient import Patient, PatientCreate, PatientUpdate, PatientSummary
from ...services.patient_service import PatientService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Patient])
async def get_patients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    language: Optional[str] = Query(None, description="Filter by preferred language"),
    db: Session = Depends(get_db)
):
    """Get all patients with optional filtering"""
    try:
        patient_service = PatientService(db)
        
        filters = {}
        if department_id:
            filters['department_id'] = department_id
        if language:
            filters['preferred_language'] = language
            
        patients = patient_service.get_patients(
            skip=skip, 
            limit=limit, 
            filters=filters
        )
        
        logger.info(f"Retrieved {len(patients)} patients")
        return patients
        
    except Exception as e:
        logger.error(f"Error retrieving patients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving patients"
        )

@router.get("/summary", response_model=List[PatientSummary])
async def get_patients_summary(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get patients summary with feedback statistics"""
    try:
        patient_service = PatientService(db)
        summaries = patient_service.get_patients_summary(skip=skip, limit=limit)
        
        logger.info(f"Retrieved {len(summaries)} patient summaries")
        return summaries
        
    except Exception as e:
        logger.error(f"Error retrieving patient summaries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving patient summaries"
        )

@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """Get patient by ID"""
    try:
        patient_service = PatientService(db)
        patient = patient_service.get_patient(patient_id)
        
        if not patient:
            logger.warning(f"Patient {patient_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        logger.info(f"Retrieved patient {patient_id}")
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving patient"
        )

@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
async def create_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    """Create new patient"""
    try:
        patient_service = PatientService(db)
        
        # Check if department exists
        if not patient_service.department_exists(patient_data.department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department not found"
            )
        
        patient = patient_service.create_patient(patient_data)
        
        logger.info(f"Created patient {patient.id}")
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating patient"
        )

@router.put("/{patient_id}", response_model=Patient)
async def update_patient(
    patient_id: int, 
    patient_data: PatientUpdate, 
    db: Session = Depends(get_db)
):
    """Update patient"""
    try:
        patient_service = PatientService(db)
        
        # Check if patient exists
        existing_patient = patient_service.get_patient(patient_id)
        if not existing_patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check if department exists (if being updated)
        if patient_data.department_id and not patient_service.department_exists(patient_data.department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department not found"
            )
        
        patient = patient_service.update_patient(patient_id, patient_data)
        
        logger.info(f"Updated patient {patient_id}")
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating patient"
        )

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    """Delete patient"""
    try:
        patient_service = PatientService(db)
        
        # Check if patient exists
        patient = patient_service.get_patient(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        # Check if patient has feedbacks
        if patient_service.patient_has_feedbacks(patient_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete patient with existing feedbacks"
            )
        
        patient_service.delete_patient(patient_id)
        
        logger.info(f"Deleted patient {patient_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting patient"
        )

@router.get("/{patient_id}/feedbacks")
async def get_patient_feedbacks(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get feedbacks for a specific patient"""
    try:
        patient_service = PatientService(db)
        
        # Check if patient exists
        patient = patient_service.get_patient(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        feedbacks = patient_service.get_patient_feedbacks(patient_id, skip=skip, limit=limit)
        
        logger.info(f"Retrieved {len(feedbacks)} feedbacks for patient {patient_id}")
        return feedbacks
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feedbacks for patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving patient feedbacks"
        )