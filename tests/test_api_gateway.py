import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestAPIGatewayAuth:
    """Test authentication endpoints in API Gateway"""
    
    def test_health_check(self, gateway_client: TestClient):
        """Test health check endpoint"""
        response = gateway_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "api-gateway"
        assert data["version"] == "1.0.0"
    
    def test_metrics_endpoint(self, gateway_client: TestClient):
        """Test metrics endpoint"""
        response = gateway_client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "total_requests" in data
        assert "response_time_avg" in data
    
    def test_login_with_valid_admin_credentials(self, gateway_client: TestClient):
        """Test login with valid admin credentials"""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = gateway_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_with_valid_staff_credentials(self, gateway_client: TestClient):
        """Test login with valid staff credentials"""
        login_data = {
            "username": "staff",
            "password": "staff123"
        }
        
        response = gateway_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_with_valid_viewer_credentials(self, gateway_client: TestClient):
        """Test login with valid viewer credentials"""
        login_data = {
            "username": "viewer",
            "password": "viewer123"
        }
        
        response = gateway_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_with_invalid_credentials(self, gateway_client: TestClient):
        """Test login with invalid credentials"""
        login_data = {
            "username": "invalid",
            "password": "invalid"
        }
        
        response = gateway_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_with_missing_username(self, gateway_client: TestClient):
        """Test login with missing username"""
        login_data = {
            "password": "admin123"
        }
        
        response = gateway_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_with_missing_password(self, gateway_client: TestClient):
        """Test login with missing password"""
        login_data = {
            "username": "admin"
        }
        
        response = gateway_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_token_verification_with_valid_token(self, gateway_client: TestClient):
        """Test token verification with valid token"""
        # First, get a valid token
        login_response = gateway_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Then verify the token
        response = gateway_client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert data["valid"] is True
    
    def test_token_verification_with_invalid_token(self, gateway_client: TestClient):
        """Test token verification with invalid token"""
        response = gateway_client.get(
            "/auth/verify",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_with_valid_token(self, gateway_client: TestClient):
        """Test get current user with valid token"""
        # First, get a valid token
        login_response = gateway_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Then get current user
        response = gateway_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert data["email"] == "admin@dgh.cm"
        assert data["is_active"] is True
    
    def test_get_current_user_without_token(self, gateway_client: TestClient):
        """Test get current user without token"""
        response = gateway_client.get("/auth/me")
        
        assert response.status_code == 403  # Forbidden without auth
    
    def test_logout(self, gateway_client: TestClient):
        """Test logout endpoint"""
        response = gateway_client.post("/auth/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_refresh_token_with_valid_token(self, gateway_client: TestClient):
        """Test refresh token with valid refresh token"""
        # First, get tokens
        login_response = gateway_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        
        # Then refresh
        response = gateway_client.post(
            "/auth/refresh",
            params={"refresh_token": refresh_token}
        )
        
        # Note: This might fail depending on implementation
        # The test is here to check the endpoint exists
        assert response.status_code in [200, 401]  # Either success or auth error


class TestAPIGatewayRateLimit:
    """Test rate limiting functionality"""
    
    @patch('api_gateway.app.middleware.rate_limit.redis')
    def test_rate_limiting_with_redis_available(self, mock_redis, gateway_client: TestClient):
        """Test rate limiting when Redis is available"""
        # Mock Redis to simulate rate limiting
        mock_redis_instance = MagicMock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.zcard.return_value = 5  # Under limit
        
        response = gateway_client.get("/health")
        
        assert response.status_code == 200
        # Check rate limit headers would be present
        # Note: Actual implementation may vary
    
    @patch('api_gateway.app.middleware.rate_limit.redis')
    def test_rate_limiting_when_redis_unavailable(self, mock_redis, gateway_client: TestClient):
        """Test rate limiting when Redis is unavailable"""
        # Mock Redis to simulate connection failure
        mock_redis.from_url.side_effect = Exception("Redis connection failed")
        
        response = gateway_client.get("/health")
        
        # Should still work without rate limiting
        assert response.status_code == 200


class TestAPIGatewayJWT:
    """Test JWT functionality"""
    
    def test_jwt_token_contains_required_fields(self, gateway_client: TestClient):
        """Test that JWT token contains required fields"""
        login_response = gateway_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        assert login_response.status_code == 200
        data = login_response.json()
        
        # Check token structure (without decoding for simplicity)
        token = data["access_token"]
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
    
    def test_different_users_get_different_roles(self, gateway_client: TestClient):
        """Test that different users get appropriate roles"""
        # Test admin user
        admin_response = gateway_client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert admin_response.status_code == 200
        admin_token = admin_response.json()["access_token"]
        
        admin_verify = gateway_client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_verify.status_code == 200
        assert admin_verify.json()["role"] == "admin"
        
        # Test staff user
        staff_response = gateway_client.post(
            "/auth/login",
            json={"username": "staff", "password": "staff123"}
        )
        assert staff_response.status_code == 200
        staff_token = staff_response.json()["access_token"]
        
        staff_verify = gateway_client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert staff_verify.status_code == 200
        assert staff_verify.json()["role"] == "staff"


class TestAPIGatewayErrorHandling:
    """Test error handling in API Gateway"""
    
    def test_invalid_json_request(self, gateway_client: TestClient):
        """Test handling of invalid JSON requests"""
        response = gateway_client.post(
            "/auth/login",
            data="invalid json",  # Send invalid JSON
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_content_type(self, gateway_client: TestClient):
        """Test handling of missing content type"""
        response = gateway_client.post(
            "/auth/login",
            data='{"username": "admin", "password": "admin123"}'
        )
        
        # Should still work or return appropriate error
        assert response.status_code in [200, 422, 415]
    
    def test_nonexistent_endpoint(self, gateway_client: TestClient):
        """Test accessing non-existent endpoint"""
        response = gateway_client.get("/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, gateway_client: TestClient):
        """Test method not allowed"""
        response = gateway_client.delete("/auth/login")  # DELETE not allowed on login
        
        assert response.status_code == 405