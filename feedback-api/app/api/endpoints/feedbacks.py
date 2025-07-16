from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ...database.connection import get_db
from ...schemas.feedback import (
    Feedback, FeedbackCreate, FeedbackUpdate, 
    FeedbackWithAnalysis, FeedbackStats
)
from ...services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Feedback])
async def get_feedbacks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    language: Optional[str] = Query(None, description="Filter by language"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_urgent: Optional[bool] = Query(None, description="Filter by urgency"),
    min_rating: Optional[float] = Query(None, ge=1, le=5, description="Minimum rating"),
    max_rating: Optional[float] = Query(None, ge=1, le=5, description="Maximum rating"),
    db: Session = Depends(get_db)
):
    """Get all feedbacks with optional filtering"""
    try:
        feedback_service = FeedbackService(db)
        
        filters = {}
        if department_id:
            filters['department_id'] = department_id
        if patient_id:
            filters['patient_id'] = patient_id
        if language:
            filters['language'] = language
        if status:
            filters['status'] = status
        if is_urgent is not None:
            filters['is_urgent'] = is_urgent
        if min_rating:
            filters['min_rating'] = min_rating
        if max_rating:
            filters['max_rating'] = max_rating
            
        feedbacks = feedback_service.get_feedbacks(
            skip=skip, 
            limit=limit, 
            filters=filters
        )
        
        logger.info(f"Retrieved {len(feedbacks)} feedbacks")
        return feedbacks
        
    except Exception as e:
        logger.error(f"Error retrieving feedbacks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving feedbacks"
        )

@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
    db: Session = Depends(get_db)
):
    """Get feedback statistics"""
    try:
        feedback_service = FeedbackService(db)
        stats = feedback_service.get_feedback_stats(department_id=department_id, days=days)
        
        logger.info(f"Retrieved feedback statistics for {days} days")
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving feedback stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving feedback statistics"
        )

@router.get("/urgent", response_model=List[Feedback])
async def get_urgent_feedbacks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get urgent feedbacks"""
    try:
        feedback_service = FeedbackService(db)
        urgent_feedbacks = feedback_service.get_urgent_feedbacks(skip=skip, limit=limit)
        
        logger.info(f"Retrieved {len(urgent_feedbacks)} urgent feedbacks")
        return urgent_feedbacks
        
    except Exception as e:
        logger.error(f"Error retrieving urgent feedbacks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving urgent feedbacks"
        )

@router.get("/{feedback_id}", response_model=FeedbackWithAnalysis)
async def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Get feedback by ID with analysis"""
    try:
        feedback_service = FeedbackService(db)
        feedback = feedback_service.get_feedback_with_analysis(feedback_id)
        
        if not feedback:
            logger.warning(f"Feedback {feedback_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )
        
        logger.info(f"Retrieved feedback {feedback_id}")
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feedback {feedback_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving feedback"
        )

@router.post("/", response_model=Feedback, status_code=status.HTTP_201_CREATED)
async def create_feedback(feedback_data: FeedbackCreate, db: Session = Depends(get_db)):
    """Create new feedback"""
    try:
        feedback_service = FeedbackService(db)
        
        # Validate patient and department exist
        if not feedback_service.patient_exists(feedback_data.patient_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient not found"
            )
            
        if not feedback_service.department_exists(feedback_data.department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department not found"
            )
        
        feedback = feedback_service.create_feedback(feedback_data)
        
        logger.info(f"Created feedback {feedback.id}")
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating feedback"
        )

@router.put("/{feedback_id}", response_model=Feedback)
async def update_feedback(
    feedback_id: int, 
    feedback_data: FeedbackUpdate, 
    db: Session = Depends(get_db)
):
    """Update feedback"""
    try:
        feedback_service = FeedbackService(db)
        
        # Check if feedback exists
        existing_feedback = feedback_service.get_feedback(feedback_id)
        if not existing_feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )
        
        feedback = feedback_service.update_feedback(feedback_id, feedback_data)
        
        logger.info(f"Updated feedback {feedback_id}")
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback {feedback_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating feedback"
        )

@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Delete feedback"""
    try:
        feedback_service = FeedbackService(db)
        
        # Check if feedback exists
        feedback = feedback_service.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )
        
        feedback_service.delete_feedback(feedback_id)
        
        logger.info(f"Deleted feedback {feedback_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback {feedback_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting feedback"
        )

@router.post("/{feedback_id}/mark-urgent")
async def mark_feedback_urgent(feedback_id: int, db: Session = Depends(get_db)):
    """Mark feedback as urgent"""
    try:
        feedback_service = FeedbackService(db)
        
        # Check if feedback exists
        feedback = feedback_service.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )
        
        updated_feedback = feedback_service.mark_urgent(feedback_id)
        
        logger.info(f"Marked feedback {feedback_id} as urgent")
        return {"message": "Feedback marked as urgent", "feedback": updated_feedback}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking feedback {feedback_id} as urgent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error marking feedback as urgent"
        )

@router.post("/{feedback_id}/resolve")
async def resolve_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Mark feedback as resolved"""
    try:
        feedback_service = FeedbackService(db)
        
        # Check if feedback exists
        feedback = feedback_service.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found"
            )
        
        updated_feedback = feedback_service.resolve_feedback(feedback_id)
        
        logger.info(f"Resolved feedback {feedback_id}")
        return {"message": "Feedback resolved", "feedback": updated_feedback}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving feedback {feedback_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resolving feedback"
        )