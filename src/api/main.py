"""
LogiFlow - FastAPI Application
API for supply chain network optimization queries and analysis
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import pandas as pd
import pickle

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.network_optimizer import NetworkOptimizer

# Initialize FastAPI app
app = FastAPI(
    title="LogiFlow - Supply Chain Network Optimizer",
    description="Optimize warehouse locations and routing to minimize costs",
    version="1.0.0"
)

# Load solution and data
solution = None
warehouse_df = None
demand_df = None
distance_df = None

try:
    with open('../../models/network_solution.pkl', 'rb') as f:
        solution = pickle.load(f)
    warehouse_df = pd.read_csv('../../data/processed/warehouse_locations.csv')
    demand_df = pd.read_csv('../../data/processed/aggregated_demand.csv')
    distance_df = pd.read_csv('../../data/raw/distance_matrix.csv')
    print("Successfully loaded optimization solution and data")
except Exception as e:
    print(f"Warning: Could not load data - {e}")

# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class OptimizationRequest(BaseModel):
    max_warehouses: Optional[int] = None
    service_level: str = "Standard"

class WarehouseInfo(BaseModel):
    name: str
    lat: float
    lon: float
    region: str
    fixed_cost: float
    is_open: bool

class RouteInfo(BaseModel):
    warehouse: str
    customer: str
    shipments: float
    cost_per_shipment: float
    total_cost: float

class OptimizationResponse(BaseModel):
    open_warehouses: List[str]
    num_warehouses: int
    total_cost: float
    fixed_cost: float
    variable_cost: float
    annual_savings: float
    savings_percentage: float
    routes: List[RouteInfo]

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "message": "LogiFlow API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/solution")
def get_solution():
    """
    Get current optimization solution
    """
    if not solution:
        raise HTTPException(status_code=500, detail="Solution not loaded")
    
    baseline_cost = 22_667_407  # From data generation
    savings = baseline_cost - solution['total_cost']
    savings_pct = (savings / baseline_cost) * 100
    
    return {
        "open_warehouses": solution['open_warehouses'],
        "num_warehouses": solution['num_warehouses'],
        "total_cost": solution['total_cost'],
        "fixed_cost": solution['fixed_cost'],
        "variable_cost": solution['variable_cost'],
        "baseline_cost": baseline_cost,
        "annual_savings": savings,
        "savings_percentage": round(savings_pct, 2),
        "num_routes": len(solution['routes'])
    }

@app.get("/warehouses")
def get_warehouses():
    """
    Get all warehouse locations with open/closed status
    """
    if warehouse_df is None or solution is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    warehouses = []
    open_whs = solution['open_warehouses']
    
    for _, wh in warehouse_df.iterrows():
        warehouses.append({
            "name": wh['warehouse'],
            "lat": wh['lat'],
            "lon": wh['lon'],
            "region": wh['region'],
            "fixed_cost": wh['fixed_cost_annual'],
            "is_open": wh['warehouse'] in open_whs
        })
    
    return {"warehouses": warehouses}

@app.get("/routes")
def get_routes():
    """
    Get all shipping routes from optimization
    """
    if solution is None:
        raise HTTPException(status_code=500, detail="Solution not loaded")
    
    routes = solution['routes'].to_dict(orient='records')
    return {"routes": routes}

@app.get("/demand")
def get_demand():
    """
    Get demand distribution by region and city
    """
    if demand_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    # Regional summary
    regional = demand_df.groupby('region')['demand'].sum().to_dict()
    
    # Top cities
    city_demand = demand_df.groupby('city')['demand'].sum().sort_values(ascending=False).head(10)
    top_cities = [{"city": city, "demand": int(demand)} for city, demand in city_demand.items()]
    
    return {
        "regional_demand": regional,
        "top_cities": top_cities,
        "total_demand": int(demand_df['demand'].sum())
    }

@app.get("/cost-breakdown")
def get_cost_breakdown():
    """
    Detailed cost analysis
    """
    if solution is None:
        raise HTTPException(status_code=500, detail="Solution not loaded")
    
    baseline_cost = 22_667_407
    optimized_cost = solution['total_cost']
    
    # Per warehouse breakdown
    warehouse_costs = []
    for wh in solution['open_warehouses']:
        wh_data = warehouse_df[warehouse_df['warehouse'] == wh].iloc[0]
        wh_routes = solution['routes'][solution['routes']['warehouse'] == wh]
        
        warehouse_costs.append({
            "warehouse": wh,
            "fixed_cost": wh_data['fixed_cost_annual'],
            "variable_cost": wh_routes['total_cost'].sum(),
            "total_cost": wh_data['fixed_cost_annual'] + wh_routes['total_cost'].sum(),
            "num_routes": len(wh_routes),
            "total_shipments": wh_routes['shipments'].sum()
        })
    
    return {
        "baseline_cost": baseline_cost,
        "optimized_cost": optimized_cost,
        "savings": baseline_cost - optimized_cost,
        "fixed_cost_total": solution['fixed_cost'],
        "variable_cost_total": solution['variable_cost'],
        "warehouse_breakdown": warehouse_costs
    }

@app.get("/scenarios")
def get_scenarios():
    """
    Get scenario analysis comparing different warehouse counts
    """
    try:
        scenario_df = pd.read_csv('../../data/processed/scenario_analysis.csv')
        scenarios = scenario_df.to_dict(orient='records')
        
        # Find optimal
        optimal_idx = scenario_df['total_cost'].idxmin()
        optimal = scenario_df.iloc[optimal_idx]
        
        return {
            "scenarios": scenarios,
            "optimal": {
                "warehouses": int(optimal['actual_warehouses']),
                "cost": optimal['total_cost']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load scenarios: {str(e)}")

@app.post("/optimize")
def run_optimization(request: OptimizationRequest):
    """
    Run optimization with custom parameters
    """
    try:
        optimizer = NetworkOptimizer()
        optimizer.load_data()
        optimizer.build_model(
            max_warehouses=request.max_warehouses,
            service_level_filter=request.service_level
        )
        optimizer.solve(time_limit=60)
        
        if not optimizer.solution:
            raise HTTPException(status_code=500, detail="Optimization failed")
        
        baseline_cost = 22_667_407
        savings = baseline_cost - optimizer.solution['total_cost']
        savings_pct = (savings / baseline_cost) * 100
        
        routes = [
            {
                "warehouse": r['warehouse'],
                "customer": r['customer'],
                "shipments": r['shipments'],
                "cost_per_shipment": r['cost_per_shipment'],
                "total_cost": r['total_cost']
            }
            for _, r in optimizer.solution['routes'].iterrows()
        ]
        
        return {
            "open_warehouses": optimizer.solution['open_warehouses'],
            "num_warehouses": optimizer.solution['num_warehouses'],
            "total_cost": optimizer.solution['total_cost'],
            "fixed_cost": optimizer.solution['fixed_cost'],
            "variable_cost": optimizer.solution['variable_cost'],
            "annual_savings": savings,
            "savings_percentage": round(savings_pct, 2),
            "routes": routes
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
def get_metrics():
    """
    Key performance metrics
    """
    if solution is None or demand_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    baseline_cost = 22_667_407
    optimized_cost = solution['total_cost']
    
    routes_df = solution['routes']
    
    return {
        "cost_metrics": {
            "baseline_cost": baseline_cost,
            "optimized_cost": optimized_cost,
            "annual_savings": baseline_cost - optimized_cost,
            "savings_percentage": round((baseline_cost - optimized_cost) / baseline_cost * 100, 2),
            "cost_per_shipment": round(optimized_cost / routes_df['shipments'].sum(), 2)
        },
        "network_metrics": {
            "num_warehouses": solution['num_warehouses'],
            "num_routes": len(routes_df),
            "total_shipments": routes_df['shipments'].sum(),
            "avg_shipments_per_route": round(routes_df['shipments'].mean(), 2),
            "num_customers_served": demand_df['city'].nunique()
        },
        "efficiency_metrics": {
            "utilization_rate": round(len(routes_df) / (solution['num_warehouses'] * demand_df['city'].nunique()) * 100, 2),
            "fixed_to_variable_ratio": round(solution['fixed_cost'] / solution['variable_cost'], 2)
        }
    }

# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":
    import uvicorn
    print("Starting LogiFlow API...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)