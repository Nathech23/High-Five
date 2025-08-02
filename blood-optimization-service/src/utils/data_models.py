from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class BloodType(str, Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"

class StockData(BaseModel):
    blood_type: BloodType
    current_stock: int
    daily_usage_avg: float
    expiration_days: int
    cost_per_unit: float
    collection_rate: float

class OptimizationRequest(BaseModel):
    stocks: List[StockData]
    constraints: Dict[str, float] = {}
    objective: str = "minimize_cost_waste"
    time_horizon: int = 30

class OptimizationResult(BaseModel):
    blood_type: BloodType
    recommended_order: int
    optimal_stock_level: int
    expected_cost: float
    waste_reduction: float
    service_level: float