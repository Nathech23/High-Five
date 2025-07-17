import pytest
from fastapi.testclient import TestClient
from databases import Database


class TestFeedbackAPIHealth:
    """Test health endpoints in Feedback API"""
    
    def test_root_endpoint(self, feedback_client: TestClient):
        """Test root endpoint"""
        response = feedback_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "DGH Feedback API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
        assert "timestamp" in data
    
    def test_health_check(self, feedback_client: TestClient):
        """Test basic health check"""
        response = feedback_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "feedback-api"
        assert data["version"] == "1.0.0"
    
    def test_detailed_health_check(self, feedback_client: TestClient):
        """Test detailed health check"""
        response = feedback_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data
    
    def test_readiness_check(self, feedback_client: TestClient):
        """Test readiness check"""
        response = feedback_client.get("/health/ready")
        
        # May return 200 or 503 depending on database state
        assert response.status_code in [200, 503]
    
    def test_liveness_check(self, feedback_client: TestClient):
        """Test liveness check"""
        response = feedback_client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_version_info(self, feedback_client: TestClient):
        """Test version information endpoint"""
        response = feedback_client.get("/version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "feedback-api"
        assert data["version"] == "1.0.0"
        assert "environment" in data
    
    def test_metrics_endpoint(self, feedback_client: TestClient):
        """Test metrics endpoint"""
        response = feedback_client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_patients" in data
        assert "total_feedbacks" in data
        assert "avg_rating" in data


class TestDepartmentsAPI:
    """Test departments API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_departments_empty(self, feedback_client: TestClient, test_db: Database):
        """Test getting departments when none exist"""
        response = feedback_client.get("/api/v1/departments")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_create_department(self, feedback_client: TestClient):
        """Test creating a new department"""
        department_data = {
            "name": "Test Department",
            "code": "TEST"
        }
        
        response = feedback_client.post("/api/v1/departments", json=department_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == department_data["name"]
        assert data["code"] == department_data["code"]
        assert "id" in data
        assert "created_at" in data
    
    def test_create_department_with_duplicate_code(self, feedback_client: TestClient):
        """Test creating department with duplicate code"""
        department_data = {
            "name": "Test Department",
            "code": "TEST"
        }
        
        # Create first department
        response1 = feedback_client.post("/api/v1/departments", json=department_data)
        assert response1.status_code == 201
        
        # Try to create second with same code
        department_data["name"] = "Another Department"
        response2 = feedback_client.post("/api/v1/departments", json=department_data)
        
        assert response2.status_code == 400
        data = response2.json()
        assert "already exists" in data["detail"]
    
    def test_create_department_invalid_data(self, feedback_client: TestClient):
        """Test creating department with invalid data"""
        invalid_data = {
            "name": "",  # Empty name
            "code": "TEST"
        }
        
        response = feedback_client.post("/api/v1/departments", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_get_department_by_id(self, feedback_client: TestClient):
        """Test getting department by ID"""
        # First create a department
        department_data = {
            "name": "Test Department",
            "code": "TEST"
        }
        
        create_response = feedback_client.post("/api/v1/departments", json=department_data)
        assert create_response.status_code == 201
        department_id = create_response.json()["id"]
        
        # Then get it by ID
        response = feedback_client.get(f"/api/v1/departments/{department_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == department_id
        assert data["name"] == department_data["name"]
        assert data["code"] == department_data["code"]
    
    def test_get_nonexistent_department(self, feedback_client: TestClient):
        """Test getting non-existent department"""
        response = feedback_client.get("/api/v1/departments/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_update_department(self, feedback_client: TestClient):
        """Test updating a department"""
        # First create a department
        department_data = {
            "name": "Original Department",
            "code": "ORIG"
        }
        
        create_response = feedback_client.post("/api/v1/departments", json=department_data)
        assert create_response.status_code == 201
        department_id = create_response.json()["id"]
        
        # Then update it
        update_data = {
            "name": "Updated Department",
            "code": "UPD"
        }
        
        response = feedback_client.put(f"/api/v1/departments/{department_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["code"] == update_data["code"]
    
    def test_delete_department(self, feedback_client: TestClient):
        """Test deleting a department"""
        # First create a department
        department_data = {
            "name": "To Delete Department",
            "code": "DEL"
        }
        
        create_response = feedback_client.post("/api/v1/departments", json=department_data)
        assert create_response.status_code == 201
        department_id = create_response.json()["id"]
        
        # Then delete it
        response = feedback_client.delete(f"/api/v1/departments/{department_id}")
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = feedback_client.get(f"/api/v1/departments/{department_id}")
        assert get_response.status_code == 404


class TestPatientsAPI:
    """Test patients API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_patients_empty(self, feedback_client: TestClient, test_db: Database):
        """Test getting patients when none exist"""
        response = feedback_client.get("/api/v1/patients")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_patient(self, feedback_client: TestClient):
        """Test creating a new patient"""
        # First create a department
        department_data = {"name": "Test Department", "code": "TEST"}
        dept_response = feedback_client.post("/api/v1/departments", json=department_data)
        assert dept_response.status_code == 201
        department_id = dept_response.json()["id"]
        
        # Then create a patient
        patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+237123456789",
            "email": "john.doe@test.cm",
            "preferred_language": "en",
            "department_id": department_id
        }
        
        response = feedback_client.post("/api/v1/patients", json=patient_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == patient_data["first_name"]
        assert data["last_name"] == patient_data["last_name"]
        assert data["phone"] == patient_data["phone"]
        assert data["email"] == patient_data["email"]
        assert data["preferred_language"] == patient_data["preferred_language"]
        assert data["department_id"] == department_id
        assert "id" in data
    
    def test_create_patient_invalid_department(self, feedback_client: TestClient):
        """Test creating patient with invalid department"""
        patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+237123456789",
            "email": "john.doe@test.cm",
            "preferred_language": "en",
            "department_id": 999  # Non-existent department
        }
        
        response = feedback_client.post("/api/v1/patients", json=patient_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_create_patient_invalid_data(self, feedback_client: TestClient):
        """Test creating patient with invalid data"""
        invalid_data = {
            "first_name": "",  # Empty name
            "last_name": "Doe",
            "department_id": 1
        }
        
        response = feedback_client.post("/api/v1/patients", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_get_patient_by_id(self, feedback_client: TestClient):
        """Test getting patient by ID"""
        # First create department and patient
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Test Dept", "code": "TEST"})
        department_id = dept_response.json()["id"]
        
        patient_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "preferred_language": "fr",
            "department_id": department_id
        }
        
        create_response = feedback_client.post("/api/v1/patients", json=patient_data)
        assert create_response.status_code == 201
        patient_id = create_response.json()["id"]
        
        # Then get patient by ID
        response = feedback_client.get(f"/api/v1/patients/{patient_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == patient_id
        assert data["first_name"] == patient_data["first_name"]
    
    def test_update_patient(self, feedback_client: TestClient):
        """Test updating a patient"""
        # Create department and patient first
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Test Dept", "code": "TEST"})
        department_id = dept_response.json()["id"]
        
        patient_data = {
            "first_name": "Original",
            "last_name": "Name",
            "preferred_language": "fr",
            "department_id": department_id
        }
        
        create_response = feedback_client.post("/api/v1/patients", json=patient_data)
        patient_id = create_response.json()["id"]
        
        # Update patient
        update_data = {
            "first_name": "Updated",
            "phone": "+237987654321"
        }
        
        response = feedback_client.put(f"/api/v1/patients/{patient_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        assert data["phone"] == update_data["phone"]


class TestFeedbacksAPI:
    """Test feedbacks API endpoints"""
    
    def test_get_feedbacks_empty(self, feedback_client: TestClient):
        """Test getting feedbacks when none exist"""
        response = feedback_client.get("/api/v1/feedbacks")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_feedback(self, feedback_client: TestClient):
        """Test creating a new feedback"""
        # Create department and patient first
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Test Dept", "code": "TEST"})
        department_id = dept_response.json()["id"]
        
        patient_data = {
            "first_name": "Test",
            "last_name": "Patient",
            "preferred_language": "fr",
            "department_id": department_id
        }
        patient_response = feedback_client.post("/api/v1/patients", json=patient_data)
        patient_id = patient_response.json()["id"]
        
        # Create feedback
        feedback_data = {
            "patient_id": patient_id,
            "department_id": department_id,
            "rating": 4.5,
            "feedback_text": "Excellent service, very professional staff",
            "language": "en",
            "wait_time_min": 15,
            "resolution_time_min": 30
        }
        
        response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == feedback_data["rating"]
        assert data["feedback_text"] == feedback_data["feedback_text"]
        assert data["language"] == feedback_data["language"]
        assert "id" in data
    
    def test_create_feedback_invalid_rating(self, feedback_client: TestClient):
        """Test creating feedback with invalid rating"""
        feedback_data = {
            "patient_id": 1,
            "department_id": 1,
            "rating": 6.0,  # Invalid rating > 5
            "feedback_text": "Test feedback",
            "language": "en"
        }
        
        response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
        
        assert response.status_code == 422
    
    def test_get_feedback_stats(self, feedback_client: TestClient):
        """Test getting feedback statistics"""
        response = feedback_client.get("/api/v1/feedbacks/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_feedbacks" in data
        assert "avg_rating" in data
        assert "urgent_count" in data
        assert "by_department" in data
        assert "by_language" in data
    
    def test_get_urgent_feedbacks(self, feedback_client: TestClient):
        """Test getting urgent feedbacks"""
        response = feedback_client.get("/api/v1/feedbacks/urgent")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestFeedbackAPIErrorHandling:
    """Test error handling in Feedback API"""
    
    def test_invalid_patient_id_in_feedback(self, feedback_client: TestClient):
        """Test creating feedback with invalid patient ID"""
        feedback_data = {
            "patient_id": 999,  # Non-existent patient
            "department_id": 1,
            "rating": 4.0,
            "feedback_text": "Test feedback",
            "language": "en"
        }
        
        response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
        
        assert response.status_code == 400
    
    def test_invalid_json_in_request(self, feedback_client: TestClient):
        """Test handling of invalid JSON in request"""
        response = feedback_client.post(
            "/api/v1/patients",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_method_not_allowed(self, feedback_client: TestClient):
        """Test method not allowed on endpoints"""
        response = feedback_client.patch("/api/v1/patients")  # PATCH not allowed
        
        assert response.status_code == 405
    
    def test_nonexistent_endpoint(self, feedback_client: TestClient):
        """Test accessing non-existent endpoint"""
        response = feedback_client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404


class TestFeedbackAPIValidation:
    """Test input validation in Feedback API"""
    
    def test_patient_name_validation(self, feedback_client: TestClient):
        """Test patient name validation"""
        # Create department first
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Test", "code": "TEST"})
        department_id = dept_response.json()["id"]
        
        # Test with very short name
        patient_data = {
            "first_name": "A",  # Too short
            "last_name": "B",   # Too short
            "preferred_language": "fr",
            "department_id": department_id
        }
        
        response = feedback_client.post("/api/v1/patients", json=patient_data)
        
        assert response.status_code == 422
    
    def test_feedback_text_validation(self, feedback_client: TestClient):
        """Test feedback text validation"""
        feedback_data = {
            "patient_id": 1,
            "department_id": 1,
            "rating": 4.0,
            "feedback_text": "Short",  # Too short
            "language": "en"
        }
        
        response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
        
        assert response.status_code == 422
    
    def test_language_validation(self, feedback_client: TestClient):
        """Test language validation"""
        feedback_data = {
            "patient_id": 1,
            "department_id": 1,
            "rating": 4.0,
            "feedback_text": "This is a valid feedback text",
            "language": "invalid_language"  # Invalid language
        }
        
        response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
        
        assert response.status_code == 422