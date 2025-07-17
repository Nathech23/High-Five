from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user model"""
    username: str
    email: EmailStr
    role: str = "viewer"
    is_active: bool = True

class UserCreate(UserBase):
    """User creation model"""
    password: str

class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str

class User(UserBase):
    """User response model"""
    id: int
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None
    role: Optional[str] = None

class UserInDB(User):
    """User in database model"""
    hashed_password: str