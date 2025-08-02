import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from src.utils.data_models import BloodType

logger = logging.getLogger(__name__)

class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    URGENT = "urgent"
    ROUTINE = "routine"

@dataclass
class BloodUnit:
    id: str
    blood_type: BloodType
    expiration_date: datetime
    location: str
    quality_score: float = 1.0
    collection_date: datetime = None
    
    def __post_init__(self):
        if self.collection_date is None:
            # Estimer date de collecte basée sur expiration (35 jours shelf life)
            self.collection_date = self.expiration_date - timedelta(days=35)

@dataclass
class Demand:
    id: str
    blood_type: BloodType
    quantity: int
    urgency: UrgencyLevel
    location: str
    required_by: datetime
    patient_weight: Optional[float] = None
    compatible_types: Optional[List[BloodType]] = None

class AllocationOptimizer:
    """Optimiseur d'allocation FEFO avec gestion intelligente des urgences"""
    
    def __init__(self):
        self.urgency_weights = {
            UrgencyLevel.CRITICAL: 1.0,
            UrgencyLevel.URGENT: 0.7,
            UrgencyLevel.ROUTINE: 0.3
        }
        
        self.compatibility_matrix = self._build_compatibility_matrix()
        
    def _build_compatibility_matrix(self) -> Dict[BloodType, List[BloodType]]:
        """Matrice de compatibilité donneur -> receveur"""
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
    
    def fefo_allocation(self, inventory: List[BloodUnit], 
                       demands: List[Demand]) -> Dict[str, Dict]:
        """First Expired First Out avec optimisation urgences"""
        
        allocations = {}
        remaining_inventory = inventory.copy()
        
        # Trier demandes par priorité
        sorted_demands = self._prioritize_demands(demands)
        
        for demand in sorted_demands:
            allocation_result = self._allocate_for_demand(
                demand, remaining_inventory
            )
            
            allocations[demand.id] = allocation_result
            
            # Retirer unités allouées
            allocated_unit_ids = allocation_result.get("allocated_units", [])
            remaining_inventory = [
                unit for unit in remaining_inventory 
                if unit.id not in allocated_unit_ids
            ]
            
        return allocations
    
    def _prioritize_demands(self, demands: List[Demand]) -> List[Demand]:
        """Priorise les demandes selon urgence et délai"""
        
        def priority_score(demand: Demand) -> Tuple[float, datetime]:
            urgency_weight = self.urgency_weights[demand.urgency]
            
            # Score basé sur urgence et temps restant
            time_pressure = 1.0
            if demand.required_by:
                hours_remaining = (demand.required_by - datetime.now()).total_seconds() / 3600
                time_pressure = max(0.1, min(1.0, hours_remaining / 24))  # Normaliser sur 24h
            
            # Score final (plus haut = plus prioritaire)
            score = urgency_weight * (2 - time_pressure)
            
            return (-score, demand.required_by)  # Négatif pour tri décroissant
        
        return sorted(demands, key=priority_score)
    
    def _allocate_for_demand(self, demand: Demand, 
                           available_inventory: List[BloodUnit]) -> Dict:
        """Alloue unités pour une demande spécifique"""
        
        # Filtrer unités compatibles
        compatible_units = [
            unit for unit in available_inventory
            if self._is_compatible(unit.blood_type, demand.blood_type)
            and unit.expiration_date > demand.required_by
            and self._calculate_distance(unit.location, demand.location) <= 100  # 100km max
        ]
        
        if not compatible_units:
            return {
                "allocated_units": [],
                "satisfied_quantity": 0,
                "satisfaction_rate": 0.0,
                "status": "no_compatible_units",
                "urgency": demand.urgency.value
            }
        
        # Scorer et trier unités (FEFO + qualité + proximité)
        scored_units = self._score_units_for_demand(compatible_units, demand)
        
        # Allouer selon quantité demandée
        allocated_units = []
        needed_quantity = demand.quantity
        
        for unit, score in scored_units:
            if needed_quantity <= 0:
                break
                
            allocated_units.append(unit.id)
            needed_quantity -= 1
            
        # Calculer métriques d'allocation
        satisfaction_rate = (demand.quantity - needed_quantity) / demand.quantity
        
        return {
            "allocated_units": allocated_units,
            "satisfied_quantity": demand.quantity - needed_quantity,
            "satisfaction_rate": satisfaction_rate,
            "status": "full" if satisfaction_rate >= 0.95 else "partial" if satisfaction_rate > 0 else "failed",
            "urgency": demand.urgency.value,
            "average_expiry_days": self._calculate_average_expiry(
                [unit for unit, _ in scored_units[:len(allocated_units)]]
            ),
            "allocation_score": np.mean([score for _, score in scored_units[:len(allocated_units)]]) if allocated_units else 0
        }
    
    def _score_units_for_demand(self, units: List[BloodUnit], 
                               demand: Demand) -> List[Tuple[BloodUnit, float]]:
        """Score unités pour demande spécifique"""
        
        scored_units = []
        
        for unit in units:
            # Facteur 1: FEFO (expiration proche = score élevé)
            days_to_expiry = (unit.expiration_date - datetime.now()).days
            fefo_score = 1.0 / (1 + days_to_expiry / 30)  # Normaliser sur 30 jours
            
            # Facteur 2: Qualité
            quality_score = unit.quality_score
            
            # Facteur 3: Proximité géographique
            distance = self._calculate_distance(unit.location, demand.location)
            proximity_score = 1.0 / (1 + distance / 50)  # Normaliser sur 50km
            
            # Facteur 4: Compatibilité exacte vs substitution
            compatibility_score = 1.0 if unit.blood_type == demand.blood_type else 0.8
            
            # Facteur 5: Urgence (les urgences prennent les meilleures unités)
            urgency_factor = self.urgency_weights[demand.urgency]
            
            # Score final pondéré
            final_score = (
                fefo_score * 0.4 +          # 40% FEFO
                quality_score * 0.3 +       # 30% qualité
                proximity_score * 0.2 +     # 20% proximité
                compatibility_score * 0.1   # 10% compatibilité exacte
            ) * urgency_factor
            
            scored_units.append((unit, final_score))
        
        # Trier par score décroissant
        return sorted(scored_units, key=lambda x: x[1], reverse=True)
    
    def _is_compatible(self, donor_type: BloodType, recipient_type: BloodType) -> bool:
        """Vérifie compatibilité types sanguins"""
        return recipient_type in self.compatibility_matrix.get(donor_type, [])
    
    def _calculate_distance(self, loc1: str, loc2: str) -> float:
        """Calcule distance entre locations (simulation)"""
        # Simulation simple - en production, utiliser vraies coordonnées
        location_coords = {
            "main": (0, 0),
            "north": (0, 50),
            "south": (0, -50),
            "east": (50, 0),
            "west": (-50, 0),
            "center": (0, 0)
        }
        
        coord1 = location_coords.get(loc1.lower(), (0, 0))
        coord2 = location_coords.get(loc2.lower(), (0, 0))
        
        return np.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)
    
    def _calculate_average_expiry(self, units: List[BloodUnit]) -> float:
        """Calcule nombre moyen de jours avant expiration"""
        if not units:
            return 0.0
            
        total_days = sum(
            (unit.expiration_date - datetime.now()).days 
            for unit in units
        )
        
        return total_days / len(units)
    
    def optimize_emergency_allocation(self, inventory: List[BloodUnit], 
                                    emergency_demands: List[Demand]) -> Dict[str, any]:
        """Optimisation spéciale pour situations d'urgence"""
        
        critical_demands = [d for d in emergency_demands if d.urgency == UrgencyLevel.CRITICAL]
        
        if not critical_demands:
            return {
                "allocations": self.fefo_allocation(inventory, emergency_demands),
                "emergency_mode": False
            }
        
        # Mode urgence activé
        logger.info(f"Emergency mode activated for {len(critical_demands)} critical demands")
        
        emergency_allocations = {}
        reserved_inventory = inventory.copy()
        
        # Phase 1: Traiter urgences critiques avec algorithme optimisé
        for demand in critical_demands:
            best_allocation = self._find_optimal_emergency_allocation(
                reserved_inventory, demand
            )
            
            if best_allocation:
                emergency_allocations[demand.id] = best_allocation
                # Retirer unités allouées
                allocated_ids = best_allocation["allocated_units"]
                reserved_inventory = [
                    u for u in reserved_inventory if u.id not in allocated_ids
                ]
            else:
                # Aucune allocation possible - situation critique
                emergency_allocations[demand.id] = {
                    "allocated_units": [],
                    "satisfied_quantity": 0,
                    "satisfaction_rate": 0.0,
                    "status": "critical_shortage",
                    "urgency": demand.urgency.value
                }
        
        # Phase 2: Traiter demandes non-critiques avec inventaire restant
        remaining_demands = [d for d in emergency_demands if d.urgency != UrgencyLevel.CRITICAL]
        normal_allocations = self.fefo_allocation(reserved_inventory, remaining_demands)
        
        # Combiner résultats
        all_allocations = {**emergency_allocations, **normal_allocations}
        
        return {
            "allocations": all_allocations,
            "emergency_mode": True,
            "critical_demands_handled": len(critical_demands),
            "critical_satisfaction_rate": self._calculate_critical_satisfaction(emergency_allocations),
            "total_satisfaction_rate": self._calculate_total_satisfaction(all_allocations),
            "shortage_alerts": self._generate_shortage_alerts(emergency_allocations)
        }
    
    def _find_optimal_emergency_allocation(self, inventory: List[BloodUnit], 
                                         demand: Demand) -> Optional[Dict]:
        """Trouve allocation optimale pour urgence critique"""
        
        # Élargir critères pour urgences
        compatible_units = [
            unit for unit in inventory
            if self._is_compatible(unit.blood_type, demand.blood_type)
            and unit.expiration_date > datetime.now() + timedelta(hours=6)  # Minimum 6h
        ]
        
        if not compatible_units:
            return None
        
        # Algorithme spécial urgence : prioriser qualité et proximité
        emergency_scored = []
        
        for unit in compatible_units:
            # Score urgence : qualité > proximité > expiration
            quality_weight = 0.5
            proximity_weight = 0.3
            freshness_weight = 0.2
            
            quality_score = unit.quality_score
            
            distance = self._calculate_distance(unit.location, demand.location)
            proximity_score = 1.0 / (1 + distance / 25)  # Rayon réduit pour urgences
            
            days_to_expiry = (unit.expiration_date - datetime.now()).days
            freshness_score = min(1.0, days_to_expiry / 14)  # 14 jours = score max
            
            emergency_score = (
                quality_score * quality_weight +
                proximity_score * proximity_weight +
                freshness_score * freshness_weight
            )
            
            emergency_scored.append((unit, emergency_score))
        
        # Trier par score urgence
        emergency_scored.sort(key=lambda x: x[1], reverse=True)
        
        # Allouer meilleures unités
        allocated_units = []
        needed = demand.quantity
        
        for unit, score in emergency_scored:
            if needed <= 0:
                break
            allocated_units.append(unit.id)
            needed -= 1
        
        if allocated_units:
            return {
                "allocated_units": allocated_units,
                "satisfied_quantity": demand.quantity - needed,
                "satisfaction_rate": (demand.quantity - needed) / demand.quantity,
                "status": "emergency_allocated",
                "urgency": demand.urgency.value,
                "emergency_score": np.mean([score for _, score in emergency_scored[:len(allocated_units)]]),
                "allocation_time": datetime.now().isoformat()
            }
        
        return None
    
    def _calculate_critical_satisfaction(self, critical_allocations: Dict) -> float:
        """Calcule taux satisfaction demandes critiques"""
        if not critical_allocations:
            return 0.0
            
        total_satisfaction = sum(
            alloc.get("satisfaction_rate", 0) 
            for alloc in critical_allocations.values()
        )
        
        return total_satisfaction / len(critical_allocations)
    
    def _calculate_total_satisfaction(self, all_allocations: Dict) -> float:
        """Calcule taux satisfaction global"""
        if not all_allocations:
            return 0.0
            
        total_satisfaction = sum(
            alloc.get("satisfaction_rate", 0) 
            for alloc in all_allocations.values()
        )
        
        return total_satisfaction / len(all_allocations)
    
    def _generate_shortage_alerts(self, critical_allocations: Dict) -> List[Dict]:
        """Génère alertes pour pénuries critiques"""
        alerts = []
        
        for demand_id, allocation in critical_allocations.items():
            if allocation.get("satisfaction_rate", 0) < 0.8:  # Moins de 80% satisfait
                alerts.append({
                    "demand_id": demand_id,
                    "shortage_severity": "high" if allocation.get("satisfaction_rate", 0) < 0.5 else "medium",
                    "missing_units": allocation.get("satisfied_quantity", 0),
                    "status": allocation.get("status", "unknown"),
                    "recommendation": "urgent_procurement" if allocation.get("satisfaction_rate", 0) == 0 else "alternative_sourcing"
                })
        
        return alerts
    
    def get_allocation_metrics(self, allocations: Dict) -> Dict:
        """Calcule métriques détaillées d'allocation"""
        
        if not allocations:
            return {
                "total_demands": 0,
                "total_satisfied": 0,
                "overall_satisfaction_rate": 0.0
            }
        
        total_demands = len(allocations)
        fully_satisfied = sum(1 for a in allocations.values() if a.get("satisfaction_rate", 0) >= 0.95)
        
        satisfaction_rates = [a.get("satisfaction_rate", 0) for a in allocations.values()]
        avg_satisfaction = np.mean(satisfaction_rates) if satisfaction_rates else 0.0
        
        urgency_breakdown = {}
        for allocation in allocations.values():
            urgency = allocation.get("urgency", "unknown")
            if urgency not in urgency_breakdown:
                urgency_breakdown[urgency] = {"count": 0, "avg_satisfaction": 0.0}
            urgency_breakdown[urgency]["count"] += 1
        
        # Calculer satisfaction moyenne par urgence
        for urgency in urgency_breakdown:
            urgency_satisfactions = [
                a.get("satisfaction_rate", 0) 
                for a in allocations.values() 
                if a.get("urgency") == urgency
            ]
            urgency_breakdown[urgency]["avg_satisfaction"] = np.mean(urgency_satisfactions)
        
        return {
            "total_demands": total_demands,
            "fully_satisfied": fully_satisfied,
            "partially_satisfied": sum(1 for a in allocations.values() 
                                     if 0 < a.get("satisfaction_rate", 0) < 0.95),
            "unsatisfied": sum(1 for a in allocations.values() 
                             if a.get("satisfaction_rate", 0) == 0),
            "overall_satisfaction_rate": round(avg_satisfaction, 3),
            "satisfaction_distribution": {
                "min": round(min(satisfaction_rates) if satisfaction_rates else 0, 3),
                "max": round(max(satisfaction_rates) if satisfaction_rates else 0, 3),
                "std": round(np.std(satisfaction_rates) if satisfaction_rates else 0, 3)
            },
            "urgency_breakdown": urgency_breakdown,
            "performance_score": self._calculate_performance_score(allocations)
        }
    
    def _calculate_performance_score(self, allocations: Dict) -> float:
        """Calcule score performance global (0-100)"""
        if not allocations:
            return 0.0
        
        # Facteurs de performance
        satisfaction_rates = [a.get("satisfaction_rate", 0) for a in allocations.values()]
        avg_satisfaction = np.mean(satisfaction_rates)
        
        # Pénaliser les échecs complets plus fortement
        failure_penalty = sum(1 for rate in satisfaction_rates if rate == 0) / len(satisfaction_rates)
        
        # Bonus pour urgences bien gérées
        critical_bonus = 0
        critical_allocations = [a for a in allocations.values() if a.get("urgency") == "critical"]
        if critical_allocations:
            critical_satisfaction = np.mean([a.get("satisfaction_rate", 0) for a in critical_allocations])
            critical_bonus = (critical_satisfaction - 0.8) * 0.2 if critical_satisfaction > 0.8 else 0
        
        # Score final
        base_score = avg_satisfaction * 100
        penalty = failure_penalty * 30  # -30 points par échec complet
        bonus = critical_bonus * 100
        
        return max(0, min(100, base_score - penalty + bonus))