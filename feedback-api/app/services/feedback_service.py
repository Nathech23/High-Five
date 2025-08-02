from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..database.models import Feedback, Patient, Department, FeedbackAnalysis
from ..schemas.feedback import FeedbackCreate, FeedbackUpdate, FeedbackStats

logger = logging.getLogger(__name__)

class FeedbackService:
    """Service class for feedback operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_feedbacks(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Feedback]:
        """Get feedbacks with optional filtering"""
        query = self.db.query(Feedback)
        
        if filters:
            if 'department_id' in filters:
                query = query.filter(Feedback.department_id == filters['department_id'])
            if 'patient_id' in filters:
                query = query.filter(Feedback.patient_id == filters['patient_id'])
            if 'language' in filters:
                query = query.filter(Feedback.language == filters['language'])
            if 'status' in filters:
                query = query.filter(Feedback.status == filters['status'])
            if 'is_urgent' in filters:
                query = query.filter(Feedback.is_urgent == filters['is_urgent'])
            if 'min_rating' in filters:
                query = query.filter(Feedback.rating >= filters['min_rating'])
            if 'max_rating' in filters:
                query = query.filter(Feedback.rating <= filters['max_rating'])
        
        return query.order_by(desc(Feedback.created_at)).offset(skip).limit(limit).all()
    
    def get_feedback(self, feedback_id: int) -> Optional[Feedback]:
        """Get feedback by ID"""
        return self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    def get_feedback_with_analysis(self, feedback_id: int) -> Optional[Feedback]:
        """Get feedback by ID with analysis data"""
        return self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    def create_feedback(self, feedback_data: FeedbackCreate) -> Feedback:
        """Create new feedback"""
        db_feedback = Feedback(**feedback_data.model_dump())
        
        # Auto-detect urgency based on rating and keywords
        urgency_score = self._calculate_urgency(feedback_data.feedback_text, feedback_data.rating)
        db_feedback.is_urgent = urgency_score > 0.7
        
        self.db.add(db_feedback)
        self.db.commit()
        self.db.refresh(db_feedback)
        
        logger.info(f"Created feedback {db_feedback.id} for patient {feedback_data.patient_id}")
        return db_feedback
    
    def update_feedback(self, feedback_id: int, feedback_data: FeedbackUpdate) -> Feedback:
        """Update feedback"""
        db_feedback = self.get_feedback(feedback_id)
        if not db_feedback:
            raise ValueError("Feedback not found")
        
        update_data = feedback_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_feedback, field, value)
        
        self.db.commit()
        self.db.refresh(db_feedback)
        
        logger.info(f"Updated feedback {feedback_id}")
        return db_feedback
    
    def delete_feedback(self, feedback_id: int) -> bool:
        """Delete feedback"""
        db_feedback = self.get_feedback(feedback_id)
        if not db_feedback:
            return False
        
        # Delete associated analysis first
        self.db.query(FeedbackAnalysis).filter(
            FeedbackAnalysis.feedback_id == feedback_id
        ).delete()
        
        self.db.delete(db_feedback)
        self.db.commit()
        
        logger.info(f"Deleted feedback {feedback_id}")
        return True
    
    def get_urgent_feedbacks(self, skip: int = 0, limit: int = 50) -> List[Feedback]:
        """Get urgent feedbacks"""
        return self.db.query(Feedback).filter(
            Feedback.is_urgent == True
        ).order_by(desc(Feedback.created_at)).offset(skip).limit(limit).all()
    
    def mark_urgent(self, feedback_id: int) -> Feedback:
        """Mark feedback as urgent"""
        db_feedback = self.get_feedback(feedback_id)
        if not db_feedback:
            raise ValueError("Feedback not found")
        
        db_feedback.is_urgent = True
        self.db.commit()
        self.db.refresh(db_feedback)
        
        logger.info(f"Marked feedback {feedback_id} as urgent")
        return db_feedback
    
    def resolve_feedback(self, feedback_id: int) -> Feedback:
        """Mark feedback as resolved"""
        db_feedback = self.get_feedback(feedback_id)
        if not db_feedback:
            raise ValueError("Feedback not found")
        
        db_feedback.status = "resolved"
        self.db.commit()
        self.db.refresh(db_feedback)
        
        logger.info(f"Resolved feedback {feedback_id}")
        return db_feedback
    
    def get_feedback_stats(self, department_id: Optional[int] = None, days: int = 30) -> FeedbackStats:
        """Get feedback statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        query = self.db.query(Feedback).filter(Feedback.created_at >= start_date)
        if department_id:
            query = query.filter(Feedback.department_id == department_id)
        
        feedbacks = query.all()
        
        if not feedbacks:
            return FeedbackStats(
                total_feedbacks=0,
                avg_rating=0.0,
                sentiment_distribution={},
                urgent_count=0,
                by_department={},
                by_language={},
                recent_trend=[]
            )
        
        # Calculate statistics
        total_feedbacks = len(feedbacks)
        avg_rating = sum(f.rating for f in feedbacks) / total_feedbacks
        urgent_count = sum(1 for f in feedbacks if f.is_urgent)
        
        # Department distribution
        dept_stats = {}
        for feedback in feedbacks:
            dept_id = feedback.department_id
            if dept_id not in dept_stats:
                dept_stats[dept_id] = {'count': 0, 'avg_rating': 0}
            dept_stats[dept_id]['count'] += 1
        
        # Calculate average ratings per department
        for dept_id in dept_stats:
            dept_feedbacks = [f for f in feedbacks if f.department_id == dept_id]
            dept_stats[dept_id]['avg_rating'] = sum(f.rating for f in dept_feedbacks) / len(dept_feedbacks)
        
        # Language distribution
        lang_stats = {}
        for feedback in feedbacks:
            lang = feedback.language
            if lang not in lang_stats:
                lang_stats[lang] = 0
            lang_stats[lang] += 1
        
        # Recent trend (last 7 days)
        trend = []
        for i in range(7):
            day_start = datetime.utcnow() - timedelta(days=i+1)
            day_end = datetime.utcnow() - timedelta(days=i)
            
            day_feedbacks = [f for f in feedbacks if day_start <= f.created_at < day_end]
            day_avg_rating = sum(f.rating for f in day_feedbacks) / len(day_feedbacks) if day_feedbacks else 0
            
            trend.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': len(day_feedbacks),
                'avg_rating': day_avg_rating
            })
        
        return FeedbackStats(
            total_feedbacks=total_feedbacks,
            avg_rating=avg_rating,
            sentiment_distribution={},  # Will be filled by NLP service
            urgent_count=urgent_count,
            by_department=dept_stats,
            by_language=lang_stats,
            recent_trend=trend
        )
    
    def patient_exists(self, patient_id: int) -> bool:
        """Check if patient exists"""
        return self.db.query(Patient).filter(Patient.id == patient_id).first() is not None
    
    def department_exists(self, department_id: int) -> bool:
        """Check if department exists"""
        return self.db.query(Department).filter(Department.id == department_id).first() is not None
    
    def _calculate_urgency(self, text: str, rating: float) -> float:
        """Calculate urgency score based on text and rating"""
        urgency_score = 0.0
        
        # Low rating increases urgency
        if rating <= 2:
            urgency_score += 0.4
        elif rating <= 3:
            urgency_score += 0.2
        
        # Urgent keywords (simplified)
        urgent_keywords = [
            'urgent', 'emergency', 'pain', 'douleur', 'urgent', 'urgence',
            'terrible', 'awful', 'horrible', 'disaster', 'catastrophe',
            'unacceptable', 'inacceptable', 'worst', 'pire'
        ]
        
        text_lower = text.lower()
        for keyword in urgent_keywords:
            if keyword in text_lower:
                urgency_score += 0.3
                break
        
        # Length of complaint (longer = potentially more serious)
        if len(text) > 200:
            urgency_score += 0.1
        
        return min(urgency_score, 1.0)
    
    def count_feedbacks(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total feedbacks with optional filters"""
        query = self.db.query(Feedback)
        
        if filters:
            if 'department_id' in filters:
                query = query.filter(Feedback.department_id == filters['department_id'])
            if 'is_urgent' in filters:
                query = query.filter(Feedback.is_urgent == filters['is_urgent'])
            if 'status' in filters:
                query = query.filter(Feedback.status == filters['status'])
        
        return query.count()