import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from pulp import *
import logging
from src.utils.data_models import StockData, BloodType, OptimizationResult

logger = logging.getLogger(__name__)

class BloodEOQOptimizer:
    """EOQ modifié pour produits périssables avec contraintes multiples"""
    
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
    
    def calculate_modified_eoq(self, stock_data: StockData) -> Dict[str, float]:
        """EOQ modifié pour produits périssables avec facteurs avancés"""
        
        # Paramètres EOQ classiques
        D = stock_data.daily_usage_avg * 365  # Demande annuelle
        K = stock_data.cost_per_unit * 0.1  # Coût de commande (10% du coût unitaire)
        h = stock_data.cost_per_unit * 0.25  # Coût de stockage (25% du coût unitaire)
        
        # Facteurs de périssabilité avancés
        shelf_life = stock_data.expiration_days
        spoilage_rate = self._calculate_spoilage_rate(shelf_life, stock_data.daily_usage_avg)
        
        # EOQ classique
        eoq_classic = np.sqrt(2 * D * K / h) if h > 0 else D / 12
        
        # Correction pour périssabilité (modèle de Ghare-Schrader)
        waste_factor = 1 + spoilage_rate
        decay_factor = spoilage_rate / 2  # Facteur de décroissance
        
        eoq_perishable = eoq_classic * np.sqrt((1 - decay_factor) / waste_factor)
        
        # Correction pour incertitude demande (modèle de sécurité)
        demand_volatility = self._estimate_demand_volatility(stock_data)
        safety_stock = self._calculate_safety_stock(stock_data, demand_volatility)
        
        # Correction pour taux de collection variable
        collection_uncertainty = abs(1 - stock_data.collection_rate)
        collection_factor = 1 + collection_uncertainty * 0.2
        
        # EOQ final ajusté
        eoq_final = eoq_perishable * collection_factor + safety_stock
        
        # Point de commande optimisé
        lead_time = 3  # 3 jours de délai moyen
        reorder_point = (stock_data.daily_usage_avg * lead_time) + safety_stock
        
        return {
            "eoq_classic": eoq_classic,
            "eoq_perishable": eoq_perishable,
            "eoq_final": max(stock_data.daily_usage_avg, eoq_final),  # Minimum 1 jour de demande
            "safety_stock": safety_stock,
            "spoilage_rate": spoilage_rate,
            "reorder_point": reorder_point,
            "demand_volatility": demand_volatility,
            "waste_factor": waste_factor,
            "collection_factor": collection_factor
        }
    
    def _calculate_spoilage_rate(self, shelf_life: int, daily_usage: float) -> float:
        """Calcule taux de péremption réaliste"""
        if shelf_life <= 0 or daily_usage <= 0:
            return 0.05  # 5% par défaut
        
        # Modèle basé sur la rotation des stocks
        turnover_rate = daily_usage * 365 / max(1, shelf_life * daily_usage)
        base_spoilage = 1 / shelf_life
        
        # Ajustement selon la vitesse de rotation
        if turnover_rate > 12:  # Rotation très rapide
            return base_spoilage * 0.5
        elif turnover_rate > 6:  # Rotation normale
            return base_spoilage
        else:  # Rotation lente
            return base_spoilage * 2
    
    def _estimate_demand_volatility(self, stock_data: StockData) -> float:
        """Estime la volatilité de la demande"""
        # Modèle basé sur le type sanguin et la demande moyenne
        base_volatility = {
            BloodType.O_NEG: 0.15,  # Très demandé, plus stable
            BloodType.O_POS: 0.18,
            BloodType.A_POS: 0.20,
            BloodType.A_NEG: 0.25,
            BloodType.B_POS: 0.30,
            BloodType.B_NEG: 0.35,
            BloodType.AB_POS: 0.40,  # Moins demandé, plus volatile
            BloodType.AB_NEG: 0.45
        }.get(stock_data.blood_type, 0.25)
        
        # Ajustement selon le volume
        if stock_data.daily_usage_avg > 20:
            return base_volatility * 0.8  # Gros volumes plus stables
        elif stock_data.daily_usage_avg < 5:
            return base_volatility * 1.3  # Petits volumes plus volatiles
        else:
            return base_volatility
    
    def _calculate_safety_stock(self, stock_data: StockData, volatility: float) -> float:
        """Calcule stock de sécurité optimisé"""
        lead_time = 3
        service_level_factor = 1.65  # 95% niveau de service
        
        # Variance de la demande pendant le délai
        lead_time_demand_variance = volatility * stock_data.daily_usage_avg * lead_time
        
        safety_stock = service_level_factor * np.sqrt(lead_time_demand_variance)
        
        # Contraintes min/max
        min_safety = stock_data.daily_usage_avg * 1  # Minimum 1 jour
        max_safety = stock_data.daily_usage_avg * 7  # Maximum 7 jours
        
        return max(min_safety, min(max_safety, safety_stock))
    
    def optimize_multi_constraint(self, stocks: List[StockData], 
                                constraints: Dict[str, float]) -> List[OptimizationResult]:
        """Optimisation multi-contraintes avec programmation linéaire"""
        
        try:
            # Créer le problème d'optimisation
            prob = LpProblem("Blood_Stock_Optimization", LpMinimize)
            
            # Variables de décision
            order_vars = {}
            stock_vars = {}
            waste_vars = {}
            shortage_vars = {}
            
            for stock in stocks:
                bt = stock.blood_type.value
                order_vars[bt] = LpVariable(f"order_{bt}", lowBound=0, cat='Integer')
                stock_vars[bt] = LpVariable(f"stock_{bt}", lowBound=0)
                waste_vars[bt] = LpVariable(f"waste_{bt}", lowBound=0)
                shortage_vars[bt] = LpVariable(f"shortage_{bt}", lowBound=0)
            
            # Fonction objectif : minimiser coût total + pénalités
            total_cost = 0
            for stock in stocks:
                bt = stock.blood_type.value
                
                # Coûts directs
                ordering_cost = order_vars[bt] * stock.cost_per_unit * 0.1
                holding_cost = stock_vars[bt] * stock.cost_per_unit * 0.25 / 365
                
                # Pénalités
                waste_penalty = waste_vars[bt] * stock.cost_per_unit * 3  # 3x le coût
                shortage_penalty = shortage_vars[bt] * stock.cost_per_unit * 5  # 5x le coût
                
                total_cost += ordering_cost + holding_cost + waste_penalty + shortage_penalty
            
            prob += total_cost
            
            # Contraintes pour chaque type sanguin
            for stock in stocks:
                bt = stock.blood_type.value
                eoq_data = self.calculate_modified_eoq(stock)
                
                # Contrainte de conservation des stocks
                projected_stock = stock.current_stock + order_vars[bt] - stock.daily_usage_avg * 7
                prob += stock_vars[bt] == projected_stock
                
                # Contrainte de gaspillage (péremption)
                spoilage_estimate = max(0, stock.current_stock * eoq_data["spoilage_rate"])
                prob += waste_vars[bt] >= spoilage_estimate
                
                # Contrainte de pénurie
                min_required = eoq_data["safety_stock"]
                prob += shortage_vars[bt] >= min_required - stock_vars[bt]
                
                # Contrainte de service minimum (90%)
                service_requirement = stock.daily_usage_avg * 7 * 0.9
                prob += stock_vars[bt] + shortage_vars[bt] >= service_requirement
                
                # Contraintes sur les commandes (réalistes)
                max_order = stock.daily_usage_avg * 30  # Maximum 30 jours
                prob += order_vars[bt] <= max_order
            
            # Contraintes globales
            if 'max_budget' in constraints:
                total_order_cost = sum(order_vars[stock.blood_type.value] * stock.cost_per_unit 
                                     for stock in stocks)
                prob += total_order_cost <= constraints['max_budget']
            
            if 'max_storage_capacity' in constraints:
                total_stock = sum(stock_vars[stock.blood_type.value] for stock in stocks)
                prob += total_stock <= constraints['max_storage_capacity']
            
            if 'min_service_level' in constraints:
                # Contrainte globale de niveau de service
                min_service = constraints.get('min_service_level', 0.90)
                for stock in stocks:
                    bt = stock.blood_type.value
                    required_stock = stock.daily_usage_avg * 7 * min_service
                    prob += stock_vars[bt] >= required_stock
            
            # Résoudre le problème
            prob.solve(PULP_CBC_CMD(msg=0))
            
            # Extraire et formater les résultats
            results = []
            for stock in stocks:
                bt = stock.blood_type.value
                
                if prob.status == LpStatusOptimal:
                    recommended_order = int(order_vars[bt].varValue or 0)
                    optimal_stock = max(0, stock_vars[bt].varValue or 0)
                    expected_waste = max(0, waste_vars[bt].varValue or 0)
                    expected_shortage = max(0, shortage_vars[bt].varValue or 0)
                    
                    # Calculer métriques business
                    eoq_data = self.calculate_modified_eoq(stock)
                    
                    # Coût total pour ce type sanguin
                    total_cost_item = (
                        recommended_order * stock.cost_per_unit * 0.1 +  # Commande
                        optimal_stock * stock.cost_per_unit * 0.25 / 365 +  # Stockage
                        expected_waste * stock.cost_per_unit * 3 +  # Gaspillage
                        expected_shortage * stock.cost_per_unit * 5  # Pénurie
                    )
                    
                    # Métriques de performance
                    service_level = self._calculate_service_level(optimal_stock, stock.daily_usage_avg, expected_shortage)
                    waste_reduction = self._calculate_waste_reduction(expected_waste, stock.current_stock)
                    
                    results.append(OptimizationResult(
                        blood_type=stock.blood_type,
                        recommended_order=recommended_order,
                        optimal_stock_level=int(optimal_stock),
                        expected_cost=round(total_cost_item, 2),
                        waste_reduction=round(waste_reduction, 1),
                        service_level=round(service_level, 1)
                    ))
                    
                else:
                    logger.warning(f"Optimization failed for {stock.blood_type}: {LpStatus[prob.status]}")
                    # Fallback vers EOQ simple
                    eoq_data = self.calculate_modified_eoq(stock)
                    results.append(OptimizationResult(
                        blood_type=stock.blood_type,
                        recommended_order=int(eoq_data["eoq_final"]),
                        optimal_stock_level=stock.current_stock + int(eoq_data["eoq_final"]),
                        expected_cost=eoq_data["eoq_final"] * stock.cost_per_unit * 1.1,
                        waste_reduction=10.0,  # Estimation conservatrice
                        service_level=85.0   # Estimation conservatrice
                    ))
                    
            return results
            
        except Exception as e:
            logger.error(f"Multi-constraint optimization failed: {e}")
            # Fallback vers optimisation simple
            return self.optimize_basic_fallback(stocks)
    
    def _calculate_service_level(self, optimal_stock: float, daily_usage: float, shortage: float) -> float:
        """Calcule le niveau de service"""
        if daily_usage <= 0:
            return 100.0
        
        # Service level = (demande satisfaite / demande totale) * 100
        weekly_demand = daily_usage * 7
        satisfied_demand = max(0, weekly_demand - shortage)
        service_level = (satisfied_demand / weekly_demand) * 100
        
        return min(100.0, max(0.0, service_level))
    
    def _calculate_waste_reduction(self, expected_waste: float, current_stock: float) -> float:
        """Calcule la réduction de gaspillage"""
        if current_stock <= 0:
            return 0.0
        
        # Estimation du gaspillage actuel
        current_waste_estimate = current_stock * 0.15  # 15% gaspillage estimé actuel
        
        if current_waste_estimate <= 0:
            return 0.0
        
        # Réduction en pourcentage
        waste_reduction = ((current_waste_estimate - expected_waste) / current_waste_estimate) * 100
        
        return max(0.0, min(50.0, waste_reduction))  # Cap à 50% de réduction
    
    def optimize_basic_fallback(self, stocks: List[StockData]) -> List[OptimizationResult]:
        """Optimisation de fallback en cas d'échec de l'optimisation complexe"""
        results = []
        
        for stock in stocks:
            eoq_data = self.calculate_modified_eoq(stock)
            
            recommended_order = max(0, int(eoq_data["eoq_final"]))
            optimal_stock = stock.current_stock + recommended_order
            
            # Métriques simplifiées
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
            
        return results
    
    def calculate_substitution_opportunities(self, stocks: List[StockData]) -> Dict[str, List[Dict]]:
        """Calcule opportunités de substitution entre types sanguins"""
        substitutions = {}
        
        for stock in stocks:
            # Identifier stocks critiques (< 3 jours de demande)
            if stock.current_stock < stock.daily_usage_avg * 3:
                compatible_types = []
                
                for other_stock in stocks:
                    if (other_stock.blood_type != stock.blood_type and 
                        other_stock.current_stock > other_stock.daily_usage_avg * 7 and  # Stock excédentaire
                        stock.blood_type in self.compatibility_matrix.get(other_stock.blood_type, [])):
                        
                        # Calculer score de compatibilité
                        urgency_score = (3 * stock.daily_usage_avg - stock.current_stock) / stock.daily_usage_avg
                        availability_score = other_stock.current_stock / other_stock.daily_usage_avg
                        
                        # Score de priorité
                        priority_score = urgency_score * availability_score
                        
                        compatible_types.append({
                            "type": other_stock.blood_type.value,
                            "available_units": int(other_stock.current_stock),
                            "excess_days": round(other_stock.current_stock / other_stock.daily_usage_avg, 1),
                            "compatibility_score": 1.0 if other_stock.blood_type == BloodType.O_NEG else 0.8,
                            "priority_score": round(priority_score, 2),
                            "recommended_transfer": min(
                                int(stock.daily_usage_avg * 3 - stock.current_stock),
                                int(other_stock.current_stock - other_stock.daily_usage_avg * 5)
                            )
                        })
                
                if compatible_types:
                    # Trier par score de priorité
                    compatible_types.sort(key=lambda x: x["priority_score"], reverse=True)
                    substitutions[stock.blood_type.value] = compatible_types[:3]  # Top 3
                    
        return substitutions