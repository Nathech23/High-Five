from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ...database.connection import get_db
from ...database.models import Department
from ...schemas.department import Department as DepartmentSchema, DepartmentCreate, DepartmentUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[DepartmentSchema])
async def get_departments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all departments"""
    try:
        departments = db.query(Department).offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(departments)} departments")
        return departments
        
    except Exception as e:
        logger.error(f"Error retrieving departments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving departments"
        )

@router.get("/{department_id}", response_model=DepartmentSchema)
async def get_department(department_id: int, db: Session = Depends(get_db)):
    """Get department by ID"""
    try:
        department = db.query(Department).filter(Department.id == department_id).first()
        
        if not department:
            logger.warning(f"Department {department_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        logger.info(f"Retrieved department {department_id}")
        return department
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving department {department_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving department"
        )

@router.post("/", response_model=DepartmentSchema, status_code=status.HTTP_201_CREATED)
async def create_department(department_data: DepartmentCreate, db: Session = Depends(get_db)):
    """Create new department"""
    try:
        # Check if department code already exists
        existing_department = db.query(Department).filter(
            Department.code == department_data.code
        ).first()
        
        if existing_department:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department code already exists"
            )
        
        db_department = Department(**department_data.model_dump())
        db.add(db_department)
        db.commit()
        db.refresh(db_department)
        
        logger.info(f"Created department {db_department.id}: {db_department.name}")
        return db_department
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating department: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating department"
        )

@router.put("/{department_id}", response_model=DepartmentSchema)
async def update_department(
    department_id: int, 
    department_data: DepartmentUpdate, 
    db: Session = Depends(get_db)
):
    """Update department"""
    try:
        db_department = db.query(Department).filter(Department.id == department_id).first()
        
        if not db_department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if new code conflicts with existing department
        if department_data.code:
            existing_department = db.query(Department).filter(
                Department.code == department_data.code,
                Department.id != department_id
            ).first()
            
            if existing_department:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Department code already exists"
                )
        
        update_data = department_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_department, field, value)
        
        db.commit()
        db.refresh(db_department)
        
        logger.info(f"Updated department {department_id}")
        return db_department
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating department {department_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating department"
        )

@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(department_id: int, db: Session = Depends(get_db)):
    """Delete department"""
    try:
        db_department = db.query(Department).filter(Department.id == department_id).first()
        
        if not db_department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if department has patients or feedbacks
        if db_department.patients or db_department.feedbacks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete department with existing patients or feedbacks"
            )
        
        db.delete(db_department)
        db.commit()
        
        logger.info(f"Deleted department {department_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting department {department_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting department"
        )

@router.get("/{department_id}/stats")
async def get_department_stats(department_id: int, db: Session = Depends(get_db)):
    """Get department statistics"""
    try:
        department = db.query(Department).filter(Department.id == department_id).first()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Calculate statistics
        total_patients = len(department.patients)
        total_feedbacks = len(department.feedbacks)
        
        if total_feedbacks > 0:
            avg_rating = sum(f.rating for f in department.feedbacks) / total_feedbacks
            urgent_count = sum(1 for f in department.feedbacks if f.is_urgent)
        else:
            avg_rating = 0.0
            urgent_count = 0
        
        stats = {
            "department_id": department_id,
            "department_name": department.name,
            "total_patients": total_patients,
            "total_feedbacks": total_feedbacks,
            "avg_rating": round(avg_rating, 2),
            "urgent_feedbacks": urgent_count
        }
        
        logger.info(f"Retrieved stats for department {department_id}")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving department stats {department_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving department statistics"
        )