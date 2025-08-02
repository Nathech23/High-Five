import pytest
import time
import numpy as np
from src.algorithms.eoq_optimizer import BloodEOQOptimizer
from src.algorithms.allocation_optimizer import AllocationOptimizer, BloodUnit, Demand, UrgencyLevel
from src.utils.data_models import StockData, BloodType
from datetime import datetime, timedelta

class TestOptimizationPerformance:
    
    def setup_method(self):
        self.eoq_optimizer = BloodEOQOptimizer()
        self.allocation_optimizer = AllocationOptimizer()
        
    def create_test_stocks(self, count: int = 8) -> List[StockData]:
        """Crée des données de test réalistes"""
        blood_types = list(BloodType)[:count]
        stocks = []
        
        for i, bt in enumerate(blood_types):
            # Données réalistes selon type sanguin
            base_usage = {
                BloodType.O_POS: 25, BloodType.O_NEG: 20, BloodType.A_POS: 18,
                BloodType.A_NEG: 12, BloodType.B_POS: 10, BloodType.B_NEG: 8,
                BloodType.AB_POS: 6, BloodType.AB_NEG: 4
            }.get(bt, 10)
            
            stocks.append(StockData(
                blood_type=bt,
                current_stock=np.random.randint(int(base_usage * 2), int(base_usage * 8)),
                daily_usage_avg=base_usage + np.random.uniform(-3, 3),
                expiration_days=np.random.randint(21, 42),
                cost_per_unit=np.random.uniform(60, 120),
                collection_rate=np.random.uniform(0.8, 1.5)
            ))
        return stocks
    
    def test_eoq_calculation_performance(self):
        """Test performance calcul EOQ < 50ms"""
        stocks = self.create_test_stocks(8)
        
        start_time = time.time()
        
        for stock in stocks:
            result = self.eoq_optimizer.calculate_modified_eoq(stock)
            assert "eoq_final" in result
            assert result["eoq_final"] > 0
            
        execution_time = time.time() - start_time
        assert execution_time < 0.05, f"EOQ calculation too slow: {execution_time:.4f}s"
        
    def test_multi_constraint_optimization_performance(self):
        """Test optimisation multi-contraintes < 500ms"""
        stocks = self.create_test_stocks(8)
        constraints = {
            "max_budget": 100000,
            "max_storage_capacity": 2000,
            "min_service_level": 0.85
        }
        
        start_time = time.time()
        results = self.eoq_optimizer.optimize_multi_constraint(stocks, constraints)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.5, f"Multi-constraint optimization too slow: {execution_time:.3f}s"
        assert len(results) == len(stocks)
        assert all(r.service_level >= 80 for r in results), "Service level too low"
        
    def test_fefo_allocation_performance(self):
        """Test allocation FEFO < 200ms"""
        # Inventaire réaliste
        inventory = []
        for i in range(50):
            inventory.append(BloodUnit(
                id=f"unit_{i}",
                blood_type=np.random.choice(list(BloodType)),
                expiration_date=datetime.now() + timedelta(days=np.random.randint(1, 35)),
                location=f"loc_{np.random.randint(1, 4)}",
                quality_score=np.random.uniform(0.85, 1.0)
            ))
        
        # Demandes réalistes
        demands = []
        for i in range(15):
            demands.append(Demand(
                id=f"demand_{i}",
                blood_type=np.random.choice(list(BloodType)),
                quantity=np.random.randint(1, 4),
                urgency=np.random.choice(list(UrgencyLevel)),
                location=f"loc_{np.random.randint(1, 4)}",
                required_by=datetime.now() + timedelta(hours=np.random.randint(2, 48))
            ))
        
        start_time = time.time()
        allocations = self.allocation_optimizer.fefo_allocation(inventory, demands)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.2, f"FEFO allocation too slow: {execution_time:.3f}s"
        assert len(allocations) == len(demands)
        
    def test_substitution_calculation_performance(self):
        """Test calcul substitutions < 50ms"""
        stocks = self.create_test_stocks(8)
        
        # Créer situation avec stocks critiques
        stocks[0].current_stock = 5  # Critique
        stocks[1].current_stock = 200  # Excédentaire
        
        start_time = time.time()
        substitutions = self.eoq_optimizer.calculate_substitution_opportunities(stocks)
        execution_time = time.time() - start_time# HEURE 2 - ALGORITHMES CORE AVANCÉS (60min)