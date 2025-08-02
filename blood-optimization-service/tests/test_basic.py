import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.algorithms.eoq_optimizer import BloodEOQOptimizer
from src.utils.data_models import StockData, BloodType

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Blood Bank Optimization API" in data["message"]

def test_eoq_optimizer():
    """Test EOQ optimizer basique"""
    optimizer = BloodEOQOptimizer()
    
    test_stock = StockData(
        blood_type=BloodType.A_POS,
        current_stock=100,
        daily_usage_avg=10.0,
        expiration_days=35,
        cost_per_unit=75.0,
        collection_rate=1.2
    )
    
    result = optimizer.calculate_basic_eoq(test_stock)
    
    assert "eoq_classic" in result
    assert "eoq_adjusted" in result
    assert result["eoq_classic"] > 0
    assert result["eoq_adjusted"] > 0

def test_optimization_endpoint():
    """Test endpoint d'optimisation"""
    test_request = {
        "stocks": [
            {
                "blood_type": "A+",
                "current_stock": 100,
                "daily_usage_avg": 10.0,
                "expiration_days": 35,
                "cost_per_unit": 75.0,
                "collection_rate": 1.2
            }
        ],
        "constraints": {},
        "objective": "minimize_cost_waste"
    }
    
    response = client.post("/optimize", json=test_request)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["blood_type"] == "A+"
    assert data[0]["recommended_order"] >= 0