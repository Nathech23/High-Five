import pytest
import time
from datetime import datetime, timedelta
from src.algorithms.allocation_optimizer import AllocationOptimizer, BloodUnit, Demand, UrgencyLevel
from src.utils.data_models import BloodType

class TestAllocationFEFO:
    
    def setup_method(self):
        self.optimizer = AllocationOptimizer()
        
    def create_test_inventory(self, count=20):
        """Crée inventaire de test"""
        inventory = []
        blood_types = list(BloodType)
        
        for i in range(count):
            inventory.append(BloodUnit(
                id=f"unit_{i}",
                blood_type=blood_types[i % len(blood_types)],
                expiration_date=datetime.now() + timedelta(days=5 + i % 30),
                location=f"loc_{i % 3}",
                quality_score=0.8 + (i % 3) * 0.1
            ))
        
        return inventory
    
    def create_test_demands(self, count=5):
        """Crée demandes de test"""
        demands = []
        urgencies = list(UrgencyLevel)
        blood_types = list(BloodType)
        
        for i in range(count):
            demands.append(Demand(
                id=f"demand_{i}",
                blood_type=blood_types[i % len(blood_types)],
                quantity=1 + i % 3,
                urgency=urgencies[i % len(urgencies)],
                location=f"loc_{i % 3}",
                required_by=datetime.now() + timedelta(hours=6 + i * 12)
            ))
        
        return demands
    
    def test_basic_fefo_allocation(self):
        """Test allocation FEFO basique"""
        inventory = self.create_test_inventory(10)
        demands = self.create_test_demands(3)
        
        start_time = time.time()
        allocations = self.optimizer.fefo_allocation(inventory, demands)
        execution_time = time.time() - start_time
        
        # Performance
        assert execution_time < 0.2, f"FEFO allocation too slow: {execution_time:.3f}s"
        
        # Résultats
        assert len(allocations) == len(demands)
        assert all("satisfaction_rate" in alloc for alloc in allocations.values())
        
        # Au moins quelques allocations réussies
        successful_allocations = sum(
            1 for alloc in allocations.values() 
            if alloc["satisfaction_rate"] > 0
        )
        assert successful_allocations > 0
        
    def test_emergency_allocation(self):
        """Test allocation d'urgence"""
        inventory = self.create_test_inventory(15)
        
        # Créer demandes d'urgence
        emergency_demands = [
            Demand(
                id="critical_1",
                blood_type=BloodType.O_NEG,
                quantity=2,
                urgency=UrgencyLevel.CRITICAL,
                location="main",
                required_by=datetime.now() + timedelta(hours=2)
            ),
            Demand(
                id="urgent_1",
                blood_type=BloodType.A_POS,
                quantity=1,
                urgency=UrgencyLevel.URGENT,
                location="main",
                required_by=datetime.now() + timedelta(hours=6)
            )
        ]
        
        result = self.optimizer.optimize_emergency_allocation(inventory, emergency_demands)
        
        assert "emergency_mode" in result
        assert "critical_demands_handled" in result
        assert "allocations" in result
        
        # Les demandes critiques doivent être traitées en priorité
        critical_alloc = result["allocations"].get("critical_1")
        if critical_alloc:
            assert critical_alloc["urgency"] == "critical"
            
    def test_compatibility_matrix(self):
        """Test matrice de compatibilité"""
        # O- doit pouvoir donner à tous
        assert self.optimizer._is_compatible(BloodType.O_NEG, BloodType.AB_POS)
        assert self.optimizer._is_compatible(BloodType.O_NEG, BloodType.A_POS)
        
        # AB+ ne peut donner qu'à AB+
        assert self.optimizer._is_compatible(BloodType.AB_POS, BloodType.AB_POS)
        assert not self.optimizer._is_compatible(BloodType.AB_POS, BloodType.A_POS)
        
        # A+ peut donner à A+ et AB+
        assert self.optimizer._is_compatible(BloodType.A_POS, BloodType.A_POS)
        assert self.optimizer._is_compatible(BloodType.A_POS, BloodType.AB_POS)
        assert not self.optimizer._is_compatible(BloodType.A_POS, BloodType.B_POS)
        
    def test_performance_with_large_dataset(self):
        """Test performance avec gros dataset"""
        # Gros inventaire
        large_inventory = self.create_test_inventory(100)
        large_demands = self.create_test_demands(25)
        
        start_time = time.time()
        allocations = self.optimizer.fefo_allocation(large_inventory, large_demands)
        execution_time = time.time() - start_time
        
        # Doit rester rapide même avec beaucoup de données
        assert execution_time < 0.5, f"Large dataset allocation too slow: {execution_time:.3f}s"
        assert len(allocations) == len(large_demands)
        
    def test_allocation_metrics(self):
        """Test calcul métriques d'allocation"""
        inventory = self.create_test_inventory(15)
        demands = self.create_test_demands(5)
        
        allocations = self.optimizer.fefo_allocation(inventory, demands)
        metrics = self.optimizer.get_allocation_metrics(allocations)
        
        # Vérifier structure des métriques
        required_keys = [
            "total_demands", "overall_satisfaction_rate", 
            "urgency_breakdown", "performance_score"
        ]
        
        for key in required_keys:
            assert key in metrics, f"Missing metric: {key}"
            
        # Valeurs cohérentes
        assert 0 <= metrics["overall_satisfaction_rate"] <= 1.0
        assert 0 <= metrics["performance_score"] <= 100
        assert metrics["total_demands"] == len(demands)
        
    def test_edge_cases(self):
        """Test cas limites"""
        # Inventaire vide
        empty_inventory = []
        demands = self.create_test_demands(2)
        
        allocations = self.optimizer.fefo_allocation(empty_inventory, demands)
        assert all(alloc["satisfaction_rate"] == 0 for alloc in allocations.values())
        
        # Demandes impossibles (types incompatibles)
        inventory = [BloodUnit(
            id="unit_1",
            blood_type=BloodType.AB_POS,
            expiration_date=datetime.now() + timedelta(days=10),
            location="main"
        )]
        
        impossible_demand = [Demand(
            id="impossible",
            blood_type=BloodType.O_NEG,  # AB+ ne peut pas donner à O-
            quantity=1,
            urgency=UrgencyLevel.ROUTINE,
            location="main",
            required_by=datetime.now() + timedelta(hours=24)
        )]
        
        allocations = self.optimizer.fefo_allocation(inventory, impossible_demand)
        assert allocations["impossible"]["satisfaction_rate"] == 0
        assert allocations["impossible"]["status"] == "no_compatible_units"