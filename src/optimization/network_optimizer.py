"""
LogiFlow - Supply Chain Network Optimizer
Uses Linear Programming to find optimal warehouse locations and routing
"""

import pandas as pd
import numpy as np
from pulp import *
import pickle
import os

class NetworkOptimizer:
    """
    Optimize warehouse locations and routing to minimize total costs
    """
    
    def __init__(self):
        self.model = None
        self.warehouses = []
        self.customers = []
        self.distance_matrix = None
        self.solution = None
        
    def load_data(self, 
                  warehouse_file='../../data/processed/warehouse_locations.csv',
                  demand_file='../../data/processed/aggregated_demand.csv',
                  distance_file='../../data/raw/distance_matrix.csv'):
        """
        Load network data
        """
        print("📊 Loading network data...")
        
        # Load warehouse info
        self.warehouse_df = pd.read_csv(warehouse_file)
        self.warehouses = self.warehouse_df['warehouse'].tolist()
        print(f"✅ Loaded {len(self.warehouses)} potential warehouses")
        
        # Load demand data
        self.demand_df = pd.read_csv(demand_file)
        self.customers = self.demand_df['city'].unique().tolist()
        print(f"✅ Loaded {len(self.customers)} customer cities")
        
        # Load distance matrix
        self.distance_df = pd.read_csv(distance_file)
        print(f"✅ Loaded distance matrix with {len(self.distance_df):,} routes")
        
    def build_model(self, max_warehouses=None, service_level_filter='Standard'):
        """
        Build linear programming optimization model
        
        Decision Variables:
        - y[w] = 1 if warehouse w is open, 0 otherwise (binary)
        - x[w,c] = flow from warehouse w to customer c (continuous)
        
        Objective:
        Minimize: Sum of (Fixed Costs) + Sum of (Variable Transport Costs)
        
        Constraints:
        1. Demand satisfaction: Each customer gets all demand met
        2. Capacity: Can't ship from closed warehouses
        3. Maximum warehouses: Optional limit on number of open warehouses
        """
        
        print("\n🔧 Building optimization model...")
        print("=" * 70)
        
        # Filter data for specific service level
        demand_filtered = self.demand_df[self.demand_df['service_level'] == service_level_filter].copy()
        distance_filtered = self.distance_df[self.distance_df['service_level'] == service_level_filter].copy()
        
        # Create demand dictionary: {customer: total_demand}
        demand_dict = demand_filtered.groupby('city')['demand'].sum().to_dict()
        
        # Create cost dictionary: {(warehouse, customer): cost_per_unit}
        cost_dict = {}
        for _, row in distance_filtered.iterrows():
            cost_dict[(row['warehouse'], row['customer_city'])] = row['transport_cost_per_shipment']
        
        # Create fixed cost dictionary: {warehouse: annual_fixed_cost}
        fixed_cost_dict = dict(zip(self.warehouse_df['warehouse'], 
                                   self.warehouse_df['fixed_cost_annual']))
        
        # Initialize LP model
        self.model = LpProblem("Supply_Chain_Network_Optimization", LpMinimize)
        
        # Decision Variables
        # y[w] = 1 if warehouse w is open
        y = LpVariable.dicts("warehouse_open", 
                             self.warehouses, 
                             cat='Binary')
        
        # x[(w,c)] = units shipped from warehouse w to customer c
        routes = [(w, c) for w in self.warehouses for c in demand_dict.keys()]
        x = LpVariable.dicts("shipment", 
                             routes, 
                             lowBound=0, 
                             cat='Continuous')
        
        # Objective Function: Minimize Total Cost
        # Total Cost = Fixed Costs + Variable Transport Costs
        self.model += (
            lpSum([fixed_cost_dict[w] * y[w] for w in self.warehouses]) +  # Fixed costs
            lpSum([cost_dict.get((w, c), 0) * x[(w, c)] for (w, c) in routes])  # Transport costs
        ), "Total_Cost"
        
        # Constraint 1: Meet all customer demand
        for c in demand_dict.keys():
            self.model += (
                lpSum([x[(w, c)] for w in self.warehouses]) == demand_dict[c],
                f"Demand_{c}"
            )
        
        # Constraint 2: Can only ship from open warehouses
        # (Big M constraint)
        M = sum(demand_dict.values())  # Big number (total demand)
        for w in self.warehouses:
            for c in demand_dict.keys():
                self.model += (
                    x[(w, c)] <= M * y[w],
                    f"Capacity_{w}_{c}"
                )
        
        # Constraint 3: Maximum number of warehouses (optional)
        if max_warehouses:
            self.model += (
                lpSum([y[w] for w in self.warehouses]) <= max_warehouses,
                "Max_Warehouses"
            )
        
        # Store variables for later access
        self.y = y
        self.x = x
        self.demand_dict = demand_dict
        self.cost_dict = cost_dict
        self.fixed_cost_dict = fixed_cost_dict
        
        print(f"✅ Model built successfully!")
        print(f"   Decision variables: {len(y)} warehouse decisions + {len(x)} routing decisions")
        print(f"   Constraints: {len(self.model.constraints)}")
        
    def solve(self, time_limit=300):
        """
        Solve the optimization model
        
        Args:
            time_limit: Maximum solving time in seconds
        """
        print("\n🚀 Solving optimization model...")
        print("   (This may take 30-60 seconds for large networks)")
        print("=" * 70)
        
        # Solve using PULP_CBC_CMD (default solver)
        solver = PULP_CBC_CMD(timeLimit=time_limit, msg=1)
        self.model.solve(solver)
        
        # Check solution status
        status = LpStatus[self.model.status]
        print(f"\n✅ Optimization Status: {status}")
        
        if status == 'Optimal':
            print("   Found optimal solution!")
        elif status == 'Feasible':
            print("   Found feasible solution (may not be optimal)")
        else:
            print(f"   ⚠️  Warning: {status}")
            return None
        
        # Extract solution
        self.extract_solution()
        
        return self.solution
    
    def extract_solution(self):
        """
        Extract and format the solution
        """
        # Find open warehouses
        open_warehouses = [w for w in self.warehouses if self.y[w].varValue > 0.5]
        
        # Extract routing decisions
        routes = []
        for (w, c) in self.x:
            flow = self.x[(w, c)].varValue
            if flow > 0.01:  # Only include significant flows
                routes.append({
                    'warehouse': w,
                    'customer': c,
                    'shipments': round(flow, 2),
                    'cost_per_shipment': self.cost_dict.get((w, c), 0),
                    'total_cost': round(flow * self.cost_dict.get((w, c), 0), 2)
                })
        
        routes_df = pd.DataFrame(routes)
        
        # Calculate costs
        total_fixed_cost = sum(self.fixed_cost_dict[w] for w in open_warehouses)
        total_variable_cost = routes_df['total_cost'].sum()
        total_cost = total_fixed_cost + total_variable_cost
        
        # Store solution
        self.solution = {
            'open_warehouses': open_warehouses,
            'num_warehouses': len(open_warehouses),
            'routes': routes_df,
            'total_cost': total_cost,
            'fixed_cost': total_fixed_cost,
            'variable_cost': total_variable_cost,
            'objective_value': value(self.model.objective)
        }
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 OPTIMIZATION RESULTS")
        print("=" * 70)
        print(f"\n🏭 Open Warehouses ({len(open_warehouses)}):")
        for w in open_warehouses:
            print(f"   ✓ {w}")
        
        print(f"\n💰 Cost Breakdown:")
        print(f"   Fixed Costs:     ${total_fixed_cost:,.0f}/year")
        print(f"   Transport Costs: ${total_variable_cost:,.0f}/year")
        print(f"   TOTAL COST:      ${total_cost:,.0f}/year")
        
        print(f"\n📦 Routing Summary:")
        print(f"   Total Routes: {len(routes_df)}")
        print(f"   Total Shipments: {routes_df['shipments'].sum():,.0f}")
        
    def compare_scenarios(self):
        """
        Compare different warehouse count scenarios
        """
        print("\n🔄 Running scenario analysis...")
        print("=" * 70)
        
        scenarios = []
        
        # Test different numbers of warehouses
        for n in [2, 3, 4, 5, 6, 7, 8]:
            print(f"\nScenario: Maximum {n} warehouses")
            self.build_model(max_warehouses=n)
            self.solve(time_limit=60)
            
            if self.solution:
                scenarios.append({
                    'max_warehouses': n,
                    'actual_warehouses': self.solution['num_warehouses'],
                    'total_cost': self.solution['total_cost'],
                    'fixed_cost': self.solution['fixed_cost'],
                    'variable_cost': self.solution['variable_cost']
                })
        
        scenario_df = pd.DataFrame(scenarios)
        
        # Find optimal
        optimal_idx = scenario_df['total_cost'].idxmin()
        optimal = scenario_df.iloc[optimal_idx]
        
        print("\n" + "=" * 70)
        print("🎯 SCENARIO COMPARISON")
        print("=" * 70)
        print(scenario_df.to_string(index=False))
        
        print(f"\n✨ OPTIMAL SOLUTION:")
        print(f"   Warehouses: {optimal['actual_warehouses']}")
        print(f"   Total Cost: ${optimal['total_cost']:,.0f}/year")
        
        return scenario_df
    
    def calculate_savings(self, baseline_cost):
        """
        Calculate savings vs baseline
        """
        if not self.solution:
            return None
        
        optimized_cost = self.solution['total_cost']
        savings = baseline_cost - optimized_cost
        savings_pct = (savings / baseline_cost) * 100
        
        print("\n" + "=" * 70)
        print("💰 BUSINESS IMPACT")
        print("=" * 70)
        print(f"Baseline Cost (all warehouses): ${baseline_cost:,.0f}/year")
        print(f"Optimized Cost:                 ${optimized_cost:,.0f}/year")
        print(f"ANNUAL SAVINGS:                 ${savings:,.0f} ({savings_pct:.1f}%)")
        print(f"3-Year Savings:                 ${savings * 3:,.0f}")
        
        return {
            'baseline_cost': baseline_cost,
            'optimized_cost': optimized_cost,
            'annual_savings': savings,
            'savings_percentage': savings_pct
        }
    
    def save_solution(self, filepath='../../models/network_solution.pkl'):
        """
        Save solution to disk
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(self.solution, f)
        print(f"\n✅ Solution saved to: {filepath}")


# ==========================================
# MAIN OPTIMIZATION SCRIPT
# ==========================================

if __name__ == "__main__":
    print("\n🚀 LogiFlow - Supply Chain Network Optimization")
    print("=" * 70)
    
    # Initialize optimizer
    optimizer = NetworkOptimizer()
    
    # Load data
    optimizer.load_data()
    
    # Build and solve model
    print("\n📍 SCENARIO 1: Unconstrained Optimization")
    optimizer.build_model(service_level_filter='Standard')
    optimizer.solve()
    
    # Calculate savings
    baseline_cost = 22_667_407  # From data generation
    optimizer.calculate_savings(baseline_cost)
    
    # Save solution
    optimizer.save_solution()
    
    # Scenario analysis
    print("\n" + "=" * 70)
    print("🔍 SCENARIO ANALYSIS: Impact of Warehouse Count")
    print("=" * 70)
    scenario_df = optimizer.compare_scenarios()
    
    # Save scenario results
    scenario_df.to_csv('../../data/processed/scenario_analysis.csv', index=False)
    print("\n✅ Scenario analysis saved to: data/processed/scenario_analysis.csv")
    
    print("\n" + "=" * 70)
    print("🎉 Optimization Complete!")
    print("=" * 70)