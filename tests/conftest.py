import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from databases import Database

# Import the applications
from api_gateway.app.main import app as gateway_app
from feedback_api.app.main import app as feedback_app
from feedback_api.app.database.models import Base
from feedback_api.app.database.connection import get_db

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test database engine
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=test_engine
)

# Test database instance
test_database = Database(TEST_DATABASE_URL)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator:
    """Create test database tables and provide database session."""
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Connect to test database
    await test_database.connect()
    
    yield test_database
    
    # Cleanup
    await test_database.disconnect()
    Base.metadata.drop_all(bind=test_engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency
feedback_app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def gateway_client() -> Generator:
    """Create test client for API Gateway."""
    with TestClient(gateway_app) as client:
        yield client

@pytest.fixture(scope="function")
def feedback_client() -> Generator:
    """Create test client for Feedback API."""
    with TestClient(feedback_app) as client:
        yield client

@pytest.fixture(scope="function")
def auth_headers(gateway_client: TestClient) -> dict:
    """Get authentication headers for testing."""
    # Login to get token
    response = gateway_client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        # Return empty headers if authentication fails
        return {}

@pytest.fixture(scope="function")
async def sample_department(test_db: Database) -> dict:
    """Create a sample department for testing."""
    department_data = {
        "name": "Test Department",
        "code": "TEST"
    }
    
    query = """
        INSERT INTO departments (name, code, created_at) 
        VALUES (:name, :code, NOW()) 
        RETURNING id, name, code
    """
    
    department_id = await test_db.execute(query, department_data)
    
    return {
        "id": department_id,
        "name": department_data["name"],
        "code": department_data["code"]
    }

@pytest.fixture(scope="function")
async def sample_patient(test_db: Database, sample_department: dict) -> dict:
    """Create a sample patient for testing."""
    patient_data = {
        "first_name": "Test",
        "last_name": "Patient",
        "phone": "+237123456789",
        "email": "test.patient@test.cm",
        "preferred_language": "fr",
        "department_id": sample_department["id"]
    }
    
    query = """
        INSERT INTO patients (first_name, last_name, phone, email, preferred_language, department_id, created_at) 
        VALUES (:first_name, :last_name, :phone, :email, :preferred_language, :department_id, NOW()) 
        RETURNING id, first_name, last_name, phone, email, preferred_language, department_id
    """
    
    patient_id = await test_db.execute(query, patient_data)
    
    return {
        "id": patient_id,
        **patient_data
    }

@pytest.fixture(scope="function")
async def sample_feedback(test_db: Database, sample_patient: dict, sample_department: dict) -> dict:
    """Create a sample feedback for testing."""
    feedback_data = {
        "patient_id": sample_patient["id"],
        "department_id": sample_department["id"],
        "rating": 4.5,
        "feedback_text": "Test feedback content for testing purposes",
        "language": "fr",
        "wait_time_min": 30,
        "resolution_time_min": 45,
        "is_urgent": False,
        "status": "pending"
    }
    
    query = """
        INSERT INTO feedbacks (patient_id, department_id, rating, feedback_text, language, wait_time_min, resolution_time_min, is_urgent, status, created_at) 
        VALUES (:patient_id, :department_id, :rating, :feedback_text, :language, :wait_time_min, :resolution_time_min, :is_urgent, :status, NOW()) 
        RETURNING id, patient_id, department_id, rating, feedback_text, language, wait_time_min, resolution_time_min, is_urgent, status
    """
    
    feedback_id = await test_db.execute(query, feedback_data)
    
    return {
        "id": feedback_id,
        **feedback_data
    }

@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis for testing."""
    class MockRedis:
        def __init__(self):
            self.data = {}
        
        def get(self, key):
            return self.data.get(key)
        
        def set(self, key, value):
            self.data[key] = value
            return True
        
        def setex(self, key, ttl, value):
            self.data[key] = value
            return True
        
        def delete(self, key):
            return self.data.pop(key, None) is not None
        
        def exists(self, key):
            return key in self.data
        
        def ping(self):
            return True
        
        def info(self):
            return {
                "used_memory_human": "1.2M",
                "connected_clients": 1,
                "total_commands_processed": 100,
                "keyspace_hits": 50,
                "keyspace_misses": 10,
                "uptime_in_seconds": 3600
            }
    
    return MockRedis()

# Test data
TEST_DEPARTMENTS = [
    {"name": "Urgences", "code": "URG"},
    {"name": "Cardiologie", "code": "CARD"},
    {"name": "Pédiatrie", "code": "PED"},
]

TEST_PATIENTS = [
    {
        "first_name": "Marie",
        "last_name": "Nguema",
        "phone": "+237670123456",
        "email": "marie.nguema@test.cm",
        "preferred_language": "fr",
        "department_id": 1
    },
    {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+237680234567",
        "email": "john.doe@test.cm",
        "preferred_language": "en",
        "department_id": 2
    }
]

TEST_FEEDBACKS = [
    {
        "patient_id": 1,
        "department_id": 1,
        "rating": 4.5,
        "feedback_text": "Excellent service, very professional staff",
        "language": "en",
        "wait_time_min": 15,
        "resolution_time_min": 30
    },
    {
        "patient_id": 2,
        "department_id": 2,
        "rating": 2.0,
        "feedback_text": "Service très lent, temps d'attente inacceptable",
        "language": "fr",
        "wait_time_min": 120,
        "resolution_time_min": 20
    }
]

@pytest.fixture(scope="function")
async def populate_test_data(test_db: Database):
    """Populate database with test data."""
    # Insert departments
    for dept in TEST_DEPARTMENTS:
        await test_db.execute(
            "INSERT INTO departments (name, code, created_at) VALUES (:name, :code, NOW())",
            dept
        )
    
    # Insert patients
    for patient in TEST_PATIENTS:
        await test_db.execute(
            """INSERT INTO patients (first_name, last_name, phone, email, preferred_language, department_id, created_at) 
               VALUES (:first_name, :last_name, :phone, :email, :preferred_language, :department_id, NOW())""",
            patient
        )
    
    # Insert feedbacks
    for feedback in TEST_FEEDBACKS:
        await test_db.execute(
            """INSERT INTO feedbacks (patient_id, department_id, rating, feedback_text, language, wait_time_min, resolution_time_min, is_urgent, status, created_at) 
               VALUES (:patient_id, :department_id, :rating, :feedback_text, :language, :wait_time_min, :resolution_time_min, false, 'pending', NOW())""",
            feedback
        )