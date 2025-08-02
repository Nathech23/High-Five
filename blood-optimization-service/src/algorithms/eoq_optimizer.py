import numpy as np
from typing import Dict, List
from src.utils.data_models import StockData, BloodType, OptimizationResult
import logging

logger = logging.getLogger(__name__)

class BloodEOQOptimizer:
    """EOQ modifié pour produits périssables - Version basique"""
    
    def __init__(self):
        self.compatibility_matrix = self._build_compatibility_matrix()
        
    def _build_compatibility_matrix(self) -> Dict[BloodType, List[BloodType]]:
        """Matrice de compatibilité des types sanguins"""
        return {
            BloodType.O_NEG: [BloodType.O_NEG, BloodType.O_POS, BloodType.A_NEG, BloodType.A_POS, 
                             BloodType.B_NEG, BloodType.B_POS, BloodType.AB_NEG, BloodType.AB_POS],
            BloodType.O_POS: [BloodType.O_POS, BloodType.A_POS, BloodType.B_POS, BloodType.AB_POS],
            BloodType.A_NEG: [BloodType.A_NEG, BloodType.A_POS, BloodType.AB_NEG, BloodType.AB_POS],
            BloodType.A_POS: [BloodType.A_POS, BloodType.AB_POS],
            BloodType.B_NEG: [BloodType.B_NEG, BloodType.B_POS, BloodType.AB_NEG, BloodType.AB_POS],
            BloodType.B_POS: [BloodType.B_POS, BloodType.AB_POS],
            BloodType.AB_NEG: [BloodType.AB_NEG, BloodType.AB_POS],
            BloodType.AB_POS: [BloodType.AB_POS]
        }
    
    def calculate_basic_eoq(self, stock_data: StockData) -> Dict[str, float]:
        """EOQ basique avec correction périssabilité"""
        
        # Paramètres EOQ
        D = stock_data.daily_usage_avg * 365  # Demande annuelle
        K = stock_data.cost_per_unit * 0.1    # Coût de commande
        h = stock_data.cost_per_unit * 0.25   # Coût de stockage
        
        # EOQ classique
        eoq_classic = np.sqrt(2 * D * K / h) if h > 0 else D / 12
        
        # Correction périssabilité
        shelf_life = stock_data.expiration_days
        spoilage_rate = max(0.01, 1 / shelf_life)
        eoq_adjusted = eoq_classic / (1 + spoilage_rate)
        
        # Safety stock
        safety_stock = np.sqrt(stock_data.daily_usage_avg * 7) * 1.65
        
        return {
            "eoq_classic": eoq_classic,
            "eoq_adjusted": eoq_adjusted,
            "safety_stock": safety_stock,
            "reorder_point": stock_data.daily_usage_avg * 7 + safety_stock,
            "spoilage_rate": spoilage_rate
        }
    
    def optimize_basic(self, stocks: List[StockData]) -> List[OptimizationResult]:
        """Optimisation basique pour chaque type sanguin"""
        
        results = []
        
        for stock in stocks:
            try:
                eoq_data = self.calculate_basic_eoq(stock)
                
                # Calculs simplifiés
                recommended_order = max(0, int(eoq_data["eoq_adjusted"]))
                optimal_stock = stock.current_stock + recommended_order
                
                # Métriques simulées (seront remplacées par vrais calculs)
                service_level = min(100, optimal_stock / (stock.daily_usage_avg * 7) * 100)
                waste_reduction = max(0, eoq_data["spoilage_rate"] * 100)
                expected_cost = recommended_order * stock.cost_per_unit * 1.1
                
                results.append(OptimizationResult(
                    blood_type=stock.blood_type,
                    recommended_order=recommended_order,
                    optimal_stock_level=int(optimal_stock),
                    expected_cost=expected_cost,
                    waste_reduction=waste_reduction,
                    service_level=service_level
                ))
                
            except Exception as e:
                logger.error(f"Optimization failed for {stock.blood_type}: {e}")
                
        return results