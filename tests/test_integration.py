import pytest
import asyncio
from fastapi.testclient import TestClient
from databases import Database


class TestFullWorkflow:
    """Test complete workflows end-to-end"""
    
    @pytest.mark.asyncio
    async def test_complete_patient_feedback_workflow(self, feedback_client: TestClient, test_db: Database):
        """Test complete workflow from patient creation to feedback submission"""
        
        # Step 1: Create a department
        department_data = {
            "name": "Integration Test Department",
            "code": "ITD"
        }
        
        dept_response = feedback_client.post("/api/v1/departments", json=department_data)
        assert dept_response.status_code == 201
        department = dept_response.json()
        department_id = department["id"]
        
        # Step 2: Create a patient
        patient_data = {
            "first_name": "Integration",
            "last_name": "Test",
            "phone": "+237123456789",
            "email": "integration.test@dgh.cm",
            "preferred_language": "fr",
            "department_id": department_id
        }
        
        patient_response = feedback_client.post("/api/v1/patients", json=patient_data)
        assert patient_response.status_code == 201
        patient = patient_response.json()
        patient_id = patient["id"]
        
        # Step 3: Submit feedback for the patient
        feedback_data = {
            "patient_id": patient_id,
            "department_id": department_id,
            "rating": 4.5,
            "feedback_text": "Service excellent dans ce département. Personnel très professionnel et temps d'attente raisonnable.",
            "language": "fr",
            "wait_time_min": 25,
            "resolution_time_min": 45
        }
        
        feedback_response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
        assert feedback_response.status_code == 201
        feedback = feedback_response.json()
        feedback_id = feedback["id"]
        
        # Step 4: Verify feedback was created correctly
        get_feedback_response = feedback_client.get(f"/api/v1/feedbacks/{feedback_id}")
        assert get_feedback_response.status_code == 200
        retrieved_feedback = get_feedback_response.json()
        
        assert retrieved_feedback["patient_id"] == patient_id
        assert retrieved_feedback["department_id"] == department_id
        assert retrieved_feedback["rating"] == 4.5
        assert retrieved_feedback["language"] == "fr"
        
        # Step 5: Verify patient's feedbacks endpoint
        patient_feedbacks_response = feedback_client.get(f"/api/v1/patients/{patient_id}/feedbacks")
        assert patient_feedbacks_response.status_code == 200
        patient_feedbacks = patient_feedbacks_response.json()
        
        assert len(patient_feedbacks) == 1
        assert patient_feedbacks[0]["id"] == feedback_id
        
        # Step 6: Get department statistics
        dept_stats_response = feedback_client.get(f"/api/v1/departments/{department_id}/stats")
        assert dept_stats_response.status_code == 200
        dept_stats = dept_stats_response.json()
        
        assert dept_stats["total_feedbacks"] == 1
        assert dept_stats["avg_rating"] == 4.5
        
        # Step 7: Get overall feedback statistics
        stats_response = feedback_client.get("/api/v1/feedbacks/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        assert stats["total_feedbacks"] >= 1
        assert department_id in [int(k) for k in stats["by_department"].keys()] or str(department_id) in stats["by_department"]
    
    @pytest.mark.asyncio
    async def test_urgent_feedback_workflow(self, feedback_client: TestClient, test_db: Database):
        """Test workflow for urgent feedback handling"""
        
        # Create department and patient
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Emergency", "code": "EMG"})
        department_id = dept_response.json()["id"]
        
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Urgent",
            "last_name": "Case",
            "preferred_language": "en",
            "department_id": department_id
        })
        patient_id = patient_response.json()["id"]
        
        # Submit urgent feedback (low rating + urgent keywords)
        urgent_feedback_data = {
            "patient_id": patient_id,
            "department_id": department_id,
            "rating": 1.0,
            "feedback_text": "This is an emergency! The service was terrible and unacceptable. I waited for hours in pain and nobody helped me!",
            "language": "en",
            "wait_time_min": 240,
            "resolution_time_min": 5
        }
        
        feedback_response = feedback_client.post("/api/v1/feedbacks", json=urgent_feedback_data)
        assert feedback_response.status_code == 201
        feedback = feedback_response.json()
        feedback_id = feedback["id"]
        
        # Verify feedback was automatically marked as urgent
        get_feedback_response = feedback_client.get(f"/api/v1/feedbacks/{feedback_id}")
        retrieved_feedback = get_feedback_response.json()
        
        # Should be marked as urgent due to low rating and urgent keywords
        assert retrieved_feedback["is_urgent"] == True
        
        # Check urgent feedbacks endpoint
        urgent_response = feedback_client.get("/api/v1/feedbacks/urgent")
        assert urgent_response.status_code == 200
        urgent_feedbacks = urgent_response.json()
        
        urgent_ids = [f["id"] for f in urgent_feedbacks]
        assert feedback_id in urgent_ids
        
        # Manually mark another feedback as urgent
        normal_feedback_response = feedback_client.post("/api/v1/feedbacks", json={
            "patient_id": patient_id,
            "department_id": department_id,
            "rating": 3.0,
            "feedback_text": "Average service, could be better",
            "language": "en"
        })
        normal_feedback_id = normal_feedback_response.json()["id"]
        
        mark_urgent_response = feedback_client.post(f"/api/v1/feedbacks/{normal_feedback_id}/mark-urgent")
        assert mark_urgent_response.status_code == 200
        
        # Verify it's now in urgent list
        urgent_response2 = feedback_client.get("/api/v1/feedbacks/urgent")
        urgent_feedbacks2 = urgent_response2.json()
        urgent_ids2 = [f["id"] for f in urgent_feedbacks2]
        assert normal_feedback_id in urgent_ids2
    
    @pytest.mark.asyncio 
    async def test_multilingual_feedback_workflow(self, feedback_client: TestClient, test_db: Database):
        """Test workflow with multiple languages"""
        
        # Create department and patient
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Multilingual Test", "code": "MLT"})
        department_id = dept_response.json()["id"]
        
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Multilingual",
            "last_name": "Patient",
            "preferred_language": "douala",
            "department_id": department_id
        })
        patient_id = patient_response.json()["id"]
        
        # Submit feedbacks in different languages
        languages_feedbacks = [
            {
                "language": "fr",
                "feedback_text": "Service excellent, personnel très professionnel et accueillant.",
                "rating": 5.0
            },
            {
                "language": "en", 
                "feedback_text": "Great service, professional staff and welcoming atmosphere.",
                "rating": 4.5
            },
            {
                "language": "douala",
                "feedback_text": "Service na nye te mboa mingi, ba salongo ba nye te ba mboa.",
                "rating": 4.0
            },
            {
                "language": "bassa",
                "feedback_text": "Service na nye te bon mingi, ba staff ba nye te na respect.",
                "rating": 4.5
            },
            {
                "language": "ewondo",
                "feedback_text": "Service na nye te mboa, ba salongo ba nye te ba mbele mingi.",
                "rating": 5.0
            }
        ]
        
        feedback_ids = []
        for lang_feedback in languages_feedbacks:
            feedback_data = {
                "patient_id": patient_id,
                "department_id": department_id,
                "rating": lang_feedback["rating"],
                "feedback_text": lang_feedback["feedback_text"],
                "language": lang_feedback["language"]
            }
            
            response = feedback_client.post("/api/v1/feedbacks", json=feedback_data)
            assert response.status_code == 201
            feedback_ids.append(response.json()["id"])
        
        # Get statistics and verify language distribution
        stats_response = feedback_client.get("/api/v1/feedbacks/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Check that all languages are represented
        by_language = stats["by_language"]
        for lang_feedback in languages_feedbacks:
            lang = lang_feedback["language"]
            assert lang in by_language
            assert by_language[lang] >= 1
        
        # Test filtering by language
        for lang in ["fr", "en", "douala"]:
            filtered_response = feedback_client.get(f"/api/v1/feedbacks?language={lang}")
            assert filtered_response.status_code == 200
            filtered_feedbacks = filtered_response.json()
            
            # All returned feedbacks should be in the requested language
            for feedback in filtered_feedbacks:
                assert feedback["language"] == lang
    
    @pytest.mark.asyncio
    async def test_feedback_status_workflow(self, feedback_client: TestClient, test_db: Database):
        """Test feedback status changes workflow"""
        
        # Create department and patient
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Status Test", "code": "ST"})
        department_id = dept_response.json()["id"]
        
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Status",
            "last_name": "Test",
            "preferred_language": "fr",
            "department_id": department_id
        })
        patient_id = patient_response.json()["id"]
        
        # Submit feedback
        feedback_response = feedback_client.post("/api/v1/feedbacks", json={
            "patient_id": patient_id,
            "department_id": department_id,
            "rating": 2.5,
            "feedback_text": "Service pourrait être amélioré, temps d'attente trop long",
            "language": "fr"
        })
        feedback_id = feedback_response.json()["id"]
        
        # Initial status should be pending
        get_response = feedback_client.get(f"/api/v1/feedbacks/{feedback_id}")
        assert get_response.json()["status"] == "pending"
        
        # Update status to reviewed
        update_response = feedback_client.put(f"/api/v1/feedbacks/{feedback_id}", json={
            "status": "reviewed"
        })
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "reviewed"
        
        # Resolve the feedback
        resolve_response = feedback_client.post(f"/api/v1/feedbacks/{feedback_id}/resolve")
        assert resolve_response.status_code == 200
        
        # Verify final status
        final_get_response = feedback_client.get(f"/api/v1/feedbacks/{feedback_id}")
        assert final_get_response.json()["status"] == "resolved"
        
        # Test filtering by status
        pending_response = feedback_client.get("/api/v1/feedbacks?status=pending")
        assert pending_response.status_code == 200
        
        resolved_response = feedback_client.get("/api/v1/feedbacks?status=resolved")
        assert resolved_response.status_code == 200
        resolved_feedbacks = resolved_response.json()
        
        resolved_ids = [f["id"] for f in resolved_feedbacks]
        assert feedback_id in resolved_ids


class TestAPIGatewayIntegration:
    """Test integration between API Gateway and Feedback API"""
    
    def test_authentication_flow_with_feedback_api(self, gateway_client: TestClient, feedback_client: TestClient):
        """Test authentication flow integrated with feedback API calls"""
        
        # Step 1: Login through API Gateway
        login_response = gateway_client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Step 2: Use token to access feedback API (simulated)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Note: In real integration, this would go through the API Gateway
        # For testing purposes, we'll verify the token structure
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT structure
        
        # Step 3: Verify token with API Gateway
        verify_response = gateway_client.get("/auth/verify", headers=headers)
        assert verify_response.status_code == 200
        
        user_info = verify_response.json()
        assert user_info["username"] == "admin"
        assert user_info["role"] == "admin"
        assert user_info["valid"] == True
    
    def test_role_based_access_simulation(self, gateway_client: TestClient):
        """Test role-based access control simulation"""
        
        # Test different user roles
        users = [
            {"username": "admin", "password": "admin123", "role": "admin"},
            {"username": "staff", "password": "staff123", "role": "staff"},
            {"username": "viewer", "password": "viewer123", "role": "viewer"}
        ]
        
        for user in users:
            # Login
            login_response = gateway_client.post("/auth/login", json={
                "username": user["username"],
                "password": user["password"]
            })
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            
            # Verify role
            verify_response = gateway_client.get("/auth/verify", headers={
                "Authorization": f"Bearer {token}"
            })
            assert verify_response.status_code == 200
            assert verify_response.json()["role"] == user["role"]
            
            # Get user info
            me_response = gateway_client.get("/auth/me", headers={
                "Authorization": f"Bearer {token}"
            })
            assert me_response.status_code == 200
            user_info = me_response.json()
            assert user_info["username"] == user["username"]
            assert user_info["role"] == user["role"]


class TestDataConsistency:
    """Test data consistency across operations"""
    
    @pytest.mark.asyncio
    async def test_patient_feedback_consistency(self, feedback_client: TestClient, test_db: Database):
        """Test data consistency between patients and their feedbacks"""
        
        # Create department
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Consistency Test", "code": "CT"})
        department_id = dept_response.json()["id"]
        
        # Create patient
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Consistency",
            "last_name": "Test",
            "preferred_language": "fr",
            "department_id": department_id
        })
        patient_id = patient_response.json()["id"]
        
        # Create multiple feedbacks
        feedback_ratings = [5.0, 4.0, 3.5, 4.5, 2.0]
        feedback_ids = []
        
        for i, rating in enumerate(feedback_ratings):
            feedback_response = feedback_client.post("/api/v1/feedbacks", json={
                "patient_id": patient_id,
                "department_id": department_id,
                "rating": rating,
                "feedback_text": f"Feedback number {i+1} for consistency testing",
                "language": "fr"
            })
            assert feedback_response.status_code == 201
            feedback_ids.append(feedback_response.json()["id"])
        
        # Get patient summary and verify feedback count
        summary_response = feedback_client.get("/api/v1/patients/summary")
        assert summary_response.status_code == 200
        summaries = summary_response.json()
        
        patient_summary = next((s for s in summaries if s["id"] == patient_id), None)
        assert patient_summary is not None
        assert patient_summary["total_feedbacks"] == len(feedback_ratings)
        
        # Calculate expected average
        expected_avg = sum(feedback_ratings) / len(feedback_ratings)
        assert abs(patient_summary["avg_rating"] - expected_avg) < 0.01
        
        # Get patient's feedbacks directly
        patient_feedbacks_response = feedback_client.get(f"/api/v1/patients/{patient_id}/feedbacks")
        patient_feedbacks = patient_feedbacks_response.json()
        
        assert len(patient_feedbacks) == len(feedback_ratings)
        
        # Verify all feedback IDs are present
        retrieved_ids = [f["id"] for f in patient_feedbacks]
        for feedback_id in feedback_ids:
            assert feedback_id in retrieved_ids
    
    @pytest.mark.asyncio
    async def test_department_statistics_consistency(self, feedback_client: TestClient, test_db: Database):
        """Test consistency of department statistics"""
        
        # Create department
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Stats Test", "code": "STA"})
        department_id = dept_response.json()["id"]
        
        # Create patients in the department
        patient_ids = []
        for i in range(3):
            patient_response = feedback_client.post("/api/v1/patients", json={
                "first_name": f"Patient{i+1}",
                "last_name": "Stats",
                "preferred_language": "en",
                "department_id": department_id
            })
            patient_ids.append(patient_response.json()["id"])
        
        # Create feedbacks for each patient
        all_ratings = []
        for patient_id in patient_ids:
            ratings = [4.0, 5.0, 3.5]  # 3 feedbacks per patient
            for rating in ratings:
                feedback_response = feedback_client.post("/api/v1/feedbacks", json={
                    "patient_id": patient_id,
                    "department_id": department_id,
                    "rating": rating,
                    "feedback_text": f"Test feedback with rating {rating}",
                    "language": "en"
                })
                assert feedback_response.status_code == 201
                all_ratings.append(rating)
        
        # Get department statistics
        dept_stats_response = feedback_client.get(f"/api/v1/departments/{department_id}/stats")
        assert dept_stats_response.status_code == 200
        dept_stats = dept_stats_response.json()
        
        # Verify consistency
        assert dept_stats["total_patients"] == len(patient_ids)
        assert dept_stats["total_feedbacks"] == len(all_ratings)
        
        expected_avg = sum(all_ratings) / len(all_ratings)
        assert abs(dept_stats["avg_rating"] - expected_avg) < 0.01
        
        # Get overall statistics and verify department is included
        overall_stats_response = feedback_client.get("/api/v1/feedbacks/stats")
        overall_stats = overall_stats_response.json()
        
        # Department should be in the breakdown
        by_dept = overall_stats["by_department"]
        dept_key = str(department_id)
        assert dept_key in by_dept or department_id in by_dept


class TestErrorHandlingIntegration:
    """Test error handling across integrated components"""
    
    def test_cascading_operations_with_errors(self, feedback_client: TestClient):
        """Test error handling when operations depend on each other"""
        
        # Try to create patient with non-existent department
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Error",
            "last_name": "Test",
            "preferred_language": "fr",
            "department_id": 999  # Non-existent
        })
        assert patient_response.status_code == 400
        
        # Try to create feedback with non-existent patient
        feedback_response = feedback_client.post("/api/v1/feedbacks", json={
            "patient_id": 999,  # Non-existent
            "department_id": 1,
            "rating": 4.0,
            "feedback_text": "This should fail",
            "language": "en"
        })
        assert feedback_response.status_code == 400
        
        # Try to delete department with associated patients (should fail)
        # First create a department and patient
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "To Delete", "code": "DEL"})
        department_id = dept_response.json()["id"]
        
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Blocking",
            "last_name": "Patient",
            "preferred_language": "fr",
            "department_id": department_id
        })
        assert patient_response.status_code == 201
        
        # Now try to delete the department (should fail)
        delete_response = feedback_client.delete(f"/api/v1/departments/{department_id}")
        assert delete_response.status_code == 400
        
    def test_concurrent_operations_simulation(self, feedback_client: TestClient):
        """Test simulation of concurrent operations"""
        
        # Create department
        dept_response = feedback_client.post("/api/v1/departments", json={"name": "Concurrent Test", "code": "CON"})
        department_id = dept_response.json()["id"]
        
        # Create patient
        patient_response = feedback_client.post("/api/v1/patients", json={
            "first_name": "Concurrent",
            "last_name": "User",
            "preferred_language": "fr", 
            "department_id": department_id
        })
        patient_id = patient_response.json()["id"]
        
        # Simulate multiple feedback submissions (would be concurrent in real scenario)
        for i in range(5):
            feedback_response = feedback_client.post("/api/v1/feedbacks", json={
                "patient_id": patient_id,
                "department_id": department_id,
                "rating": 3.0 + (i * 0.3),
                "feedback_text": f"Concurrent feedback {i+1}",
                "language": "fr"
            })
            assert feedback_response.status_code == 201
        
        # Verify all feedbacks were created
        patient_feedbacks_response = feedback_client.get(f"/api/v1/patients/{patient_id}/feedbacks")
        patient_feedbacks = patient_feedbacks_response.json()
        assert len(patient_feedbacks) == 5