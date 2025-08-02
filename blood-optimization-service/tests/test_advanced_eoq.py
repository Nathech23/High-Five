import pytest
import time
from src.algorithms.eoq_optimizer import BloodEOQOptimizer
from src.utils.data_models import StockData, BloodType

class TestAdvancedEOQ:
    
    def setup_method(self):
        self.optimizer = BloodEOQOptimizer()
        
    def create_test_stock(self, blood_type=BloodType.A_POS, critical=False):
        """Crée stock de test"""
        return StockData(
            blood_type=blood_type,
            current_stock=20 if critical else 100,
            daily_usage_avg=10.0,
            expiration_days=35,
            cost_per_unit=75.0,
            collection_rate=1.2
        )
    
    def test_modified_eoq_calculation(self):
        """Test calcul EOQ modifié"""
        stock = self.create_test_stock()
        
        result = self.optimizer.calculate_modified_eoq(stock)
        
        # Vérifications de base
        assert "eoq_final" in result
        assert "spoilage_rate" in result
        assert "safety_stock" in result
        
        # Vérifications logiques
        assert result["eoq_final"] > 0
        assert result["spoilage_rate"] >= 0
        assert result["safety_stock"] >= 0
        assert result["eoq_perishable"] <= result["eoq_classic"]  # Correction périssabilité
        
    def test_multi_constraint_optimization(self):
        """Test optimisation multi-contraintes"""
        stocks = [
            self.create_test_stock(BloodType.A_POS),
            self.create_test_stock(BloodType.O_NEG),
            self.create_test_stock(BloodType.B_POS, critical=True)
        ]
        
        constraints = {
            "max_budget": 50000,
            "max_storage_capacity": 1000,
            "min_service_level": 0.90
        }
        
        start_time = time.time()
        results = self.optimizer.optimize_multi_constraint(stocks, constraints)
        execution_time = time.time() - start_time
        
        # Performance
        assert execution_time < 0.5, f"Optimization too slow: {execution_time:.3f}s"
        
        # Résultats
        assert len(results) == 3
        assert all(r.recommended_order >= 0 for r in results)
        assert all(r.service_level >= 80 for r in results)  # Service minimum
        
        # Vérifier contrainte budget (approximativement)
        total_cost = sum(r.expected_cost for r in results)
        assert total_cost <= constraints["max_budget"] * 1.2  # Marge 20%
        
    def test_substitution_opportunities(self):
        """Test calcul substitutions"""
        stocks = [
            self.create_test_stock(BloodType.A_POS, critical=True),  # Stock critique
            self.create_test_stock(BloodType.O_NEG),  # Stock normal
            StockData(  # Stock excédentaire O-
                blood_type=BloodType.O_NEG,
                current_stock=200,
                daily_usage_avg=8.0,
                expiration_days=35,
                cost_per_unit=75.0,
                collection_rate=1.2
            )
        ]
        
        substitutions = self.optimizer.calculate_substitution_opportunities(stocks)
        
        # Doit détecter substitution pour A+ critique
        assert BloodType.A_POS.value in substitutions
        
        # Vérifier qualité des recommandations
        a_plus_subs = substitutions[BloodType.A_POS.value]
        assert len(a_plus_subs) > 0
        assert all("recommended_transfer" in sub for sub in a_plus_subs)
        
    def test_performance_requirements(self):
        """Test exigences de performance"""
        # Test avec beaucoup de types sanguins
        stocks = []
        for bt in BloodType:
            stocks.append(self.create_test_stock(bt))
            
        # EOQ doit être rapide
        start_time = time.time()
        for stock in stocks:
            self.optimizer.calculate_modified_eoq(stock)
        eoq_time = time.time() - start_time
        
        assert eoq_time < 0.1, f"EOQ calculation too slow: {eoq_time:.3f}s"
        
        # Optimisation complète
        start_time = time.time()
        results = self.optimizer.optimize_multi_constraint(stocks, {})
        opt_time = time.time() - start_time
        
        assert opt_time < 0.5, f"Multi-constraint optimization too slow: {opt_time:.3f}s"
        
    def test_edge_cases(self):
        """Test cas limites"""
        # Stock avec usage nul
        zero_usage_stock = StockData(
            blood_type=BloodType.AB_NEG,
            current_stock=50,
            daily_usage_avg=0.0,  # Usage nul
            expiration_days=35,
            cost_per_unit=75.0,
            collection_rate=1.0
        )
        
        result = self.optimizer.calculate_modified_eoq(zero_usage_stock)
        assert result["eoq_final"] >= 0  # Pas d'erreur
        
        # Stock avec expiration très courte
        short_expiry_stock = StockData(
            blood_type=BloodType.O_POS,
            current_stock=100,
            daily_usage_avg=50.0,
            expiration_days=1,  # Expire demain
            cost_per_unit=75.0,
            collection_rate=1.0
        )
        
        result = self.optimizer.calculate_modified_eoq(short_expiry_stock)
        assert result["spoilage_rate"] > 0.5  # Taux élevé
        assert result["eoq_final"] < result["eoq_classic"]  # Réduction significative
