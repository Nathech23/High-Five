from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from .config import settings
from .auth.jwt_handler import JWTHandler
from .auth.models import UserLogin, UserCreate, Token, User
from .middleware.rate_limit import RateLimitMiddleware
from .utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

# JWT Handler
jwt_handler = JWTHandler()
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting API Gateway")
    yield
    # Shutdown
    logger.info("Shutting down API Gateway")

# FastAPI app
app = FastAPI(
    title="DGH API Gateway",
    description="API Gateway with Authentication for Douala General Hospital Feedback System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "api-gateway",
        "version": "1.0.0"
    }

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    return {
        "active_connections": 1,
        "total_requests": 100,
        "response_time_avg": 0.150
    }

# Authentication endpoints
@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """Authenticate user and return JWT tokens"""
    try:
        # Validate user credentials (simplified for demo)
        if user_data.username == "admin" and user_data.password == "admin123":
            user = User(
                id=1,
                username="admin",
                email="admin@dgh.cm",
                role="admin",
                is_active=True
            )
        elif user_data.username == "staff" and user_data.password == "staff123":
            user = User(
                id=2,
                username="staff",
                email="staff@dgh.cm",
                role="staff",
                is_active=True
            )
        elif user_data.username == "viewer" and user_data.password == "viewer123":
            user = User(
                id=3,
                username="viewer",
                email="viewer@dgh.cm",
                role="viewer",
                is_active=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Generate tokens
        access_token = jwt_handler.create_access_token(data={"sub": user.username, "role": user.role})
        refresh_token = jwt_handler.create_refresh_token(data={"sub": user.username})

        logger.info(f"User {user.username} logged in successfully")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    try:
        payload = jwt_handler.decode_token(refresh_token)
        username = payload.get("sub")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get user role (simplified)
        role = "admin" if username == "admin" else "staff" if username == "staff" else "viewer"
        
        access_token = jwt_handler.create_access_token(data={"sub": username, "role": role})
        new_refresh_token = jwt_handler.create_refresh_token(data={"sub": username})

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@app.post("/auth/logout")
async def logout():
    """Logout user (token blacklisting would be implemented here)"""
    return {"message": "Successfully logged out"}

@app.get("/auth/verify")
async def verify_token(token: str = Depends(security)):
    """Verify JWT token for other services"""
    try:
        payload = jwt_handler.decode_token(token.credentials)
        username = payload.get("sub")
        role = payload.get("role")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return {
            "username": username,
            "role": role,
            "valid": True
        }

    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@app.get("/auth/me", response_model=User)
async def get_current_user(token: str = Depends(security)):
    """Get current user information"""
    try:
        payload = jwt_handler.decode_token(token.credentials)
        username = payload.get("sub")
        role = payload.get("role")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Return user info (simplified)
        user_id = 1 if username == "admin" else 2 if username == "staff" else 3
        email = f"{username}@dgh.cm"

        return User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            is_active=True
        )

    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "timestamp": time.time()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )