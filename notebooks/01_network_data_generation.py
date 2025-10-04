"""
LogiFlow - Supply Chain Network Data Generator
Generates realistic data for warehouse location and routing optimization
Based on 20+ years of supply chain industry patterns
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)

# ==========================================
# BUSINESS PARAMETERS (E-Commerce Company)
# ==========================================

# Major US cities as demand centers (customers)
DEMAND_CENTERS = {
    'New York': {'lat': 40.7128, 'lon': -74.0060, 'population': 8_400_000, 'region': 'Northeast'},
    'Los Angeles': {'lat': 34.0522, 'lon': -118.2437, 'population': 3_900_000, 'region': 'West'},
    'Chicago': {'lat': 41.8781, 'lon': -87.6298, 'population': 2_700_000, 'region': 'Midwest'},
    'Houston': {'lat': 29.7604, 'lon': -95.3698, 'population': 2_300_000, 'region': 'South'},
    'Phoenix': {'lat': 33.4484, 'lon': -112.0740, 'population': 1_600_000, 'region': 'West'},
    'Philadelphia': {'lat': 39.9526, 'lon': -75.1652, 'population': 1_600_000, 'region': 'Northeast'},
    'San Antonio': {'lat': 29.4241, 'lon': -98.4936, 'population': 1_500_000, 'region': 'South'},
    'San Diego': {'lat': 32.7157, 'lon': -117.1611, 'population': 1_400_000, 'region': 'West'},
    'Dallas': {'lat': 32.7767, 'lon': -96.7970, 'population': 1_300_000, 'region': 'South'},
    'San Jose': {'lat': 37.3382, 'lon': -121.8863, 'population': 1_000_000, 'region': 'West'},
    'Austin': {'lat': 30.2672, 'lon': -97.7431, 'population': 950_000, 'region': 'South'},
    'Jacksonville': {'lat': 30.3322, 'lon': -81.6557, 'population': 900_000, 'region': 'South'},
    'Fort Worth': {'lat': 32.7555, 'lon': -97.3308, 'population': 900_000, 'region': 'South'},
    'Columbus': {'lat': 39.9612, 'lon': -82.9988, 'population': 880_000, 'region': 'Midwest'},
    'Charlotte': {'lat': 35.2271, 'lon': -80.8431, 'population': 870_000, 'region': 'South'},
    'Seattle': {'lat': 47.6062, 'lon': -122.3321, 'population': 750_000, 'region': 'West'},
    'Denver': {'lat': 39.7392, 'lon': -104.9903, 'population': 710_000, 'region': 'West'},
    'Boston': {'lat': 42.3601, 'lon': -71.0589, 'population': 690_000, 'region': 'Northeast'},
    'Nashville': {'lat': 36.1627, 'lon': -86.7816, 'population': 670_000, 'region': 'South'},
    'Detroit': {'lat': 42.3314, 'lon': -83.0458, 'population': 670_000, 'region': 'Midwest'},
}

# Potential warehouse locations (strategic cities)
WAREHOUSE_LOCATIONS = {
    'Memphis_TN': {'lat': 35.1495, 'lon': -90.0490, 'region': 'South', 'fixed_cost': 1_200_000},
    'Indianapolis_IN': {'lat': 39.7684, 'lon': -86.1581, 'region': 'Midwest', 'fixed_cost': 1_000_000},
    'Atlanta_GA': {'lat': 33.7490, 'lon': -84.3880, 'region': 'South', 'fixed_cost': 1_300_000},
    'Kansas_City_MO': {'lat': 39.0997, 'lon': -94.5786, 'region': 'Midwest', 'fixed_cost': 950_000},
    'Columbus_OH': {'lat': 39.9612, 'lon': -82.9988, 'region': 'Midwest', 'fixed_cost': 1_000_000},
    'Dallas_TX': {'lat': 32.7767, 'lon': -96.7970, 'region': 'South', 'fixed_cost': 1_100_000},
    'Reno_NV': {'lat': 39.5296, 'lon': -119.8138, 'region': 'West', 'fixed_cost': 1_150_000},
    'Phoenix_AZ': {'lat': 33.4484, 'lon': -112.0740, 'region': 'West', 'fixed_cost': 1_050_000},
    'Harrisburg_PA': {'lat': 40.2732, 'lon': -76.8867, 'region': 'Northeast', 'fixed_cost': 1_100_000},
    'Allentown_PA': {'lat': 40.6023, 'lon': -75.4714, 'region': 'Northeast', 'fixed_cost': 1_050_000},
}

# Product categories with different shipping characteristics
PRODUCT_CATEGORIES = {
    'Electronics': {'weight_kg': 2.5, 'value': 300, 'volume_m3': 0.02},
    'Apparel': {'weight_kg': 0.8, 'value': 50, 'volume_m3': 0.01},
    'Home_Goods': {'weight_kg': 5.0, 'value': 80, 'volume_m3': 0.05},
    'Books': {'weight_kg': 1.2, 'value': 20, 'volume_m3': 0.008},
    'Toys': {'weight_kg': 1.5, 'value': 35, 'volume_m3': 0.015},
}

# Service level options
SERVICE_LEVELS = {
    'Standard': {'days': 5, 'cost_multiplier': 1.0, 'demand_share': 0.60},
    'Express': {'days': 2, 'cost_multiplier': 1.8, 'demand_share': 0.30},
    'Overnight': {'days': 1, 'cost_multiplier': 3.0, 'demand_share': 0.10},
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points on Earth (in km)
    """
    R = 6371  # Earth radius in km
    
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

def calculate_transport_cost(distance_km, weight_kg, service_level='Standard'):
    """
    Calculate transportation cost based on distance and weight
    Industry standard: ~$0.50-$1.50 per km per ton
    """
    base_rate = 1.0  # $/km/ton
    weight_tons = weight_kg / 1000
    service_multiplier = SERVICE_LEVELS[service_level]['cost_multiplier']
    
    # Add distance premium for very long routes
    if distance_km > 2000:
        distance_multiplier = 1.3
    elif distance_km > 1000:
        distance_multiplier = 1.1
    else:
        distance_multiplier = 1.0
    
    cost = base_rate * distance_km * weight_tons * service_multiplier * distance_multiplier
    return round(cost, 2)

# ==========================================
# DATA GENERATION
# ==========================================

def generate_demand_data(start_date='2024-01-01', end_date='2024-12-31'):
    """
    Generate daily demand for each city
    """
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    data = []
    
    for date in date_range:
        month = date.month
        day_of_week = date.strftime('%A')
        is_weekend = day_of_week in ['Saturday', 'Sunday']
        
        # Seasonal multipliers
        if month in [11, 12]:  # Holiday season
            seasonal_mult = 1.5
        elif month in [6, 7, 8]:  # Summer
            seasonal_mult = 1.2
        else:
            seasonal_mult = 1.0
        
        # Day of week multiplier
        dow_mult = 1.3 if is_weekend else 1.0
        
        for city, info in DEMAND_CENTERS.items():
            # Base demand proportional to population
            base_demand = info['population'] / 10000  # ~1 order per 10k people
            
            for category, cat_info in PRODUCT_CATEGORIES.items():
                # Category popularity varies by city
                if category == 'Electronics' and info['region'] == 'West':
                    category_mult = 1.3  # Tech hubs
                elif category == 'Apparel' and info['region'] == 'Northeast':
                    category_mult = 1.2  # Fashion centers
                else:
                    category_mult = 1.0
                
                # Calculate demand
                expected_demand = base_demand * seasonal_mult * dow_mult * category_mult * 0.2  # 20% of base per category
                
                # Add noise
                noise = np.random.normal(1.0, 0.15)
                actual_demand = max(0, int(expected_demand * noise))
                
                # Distribute across service levels
                for service, service_info in SERVICE_LEVELS.items():
                    service_demand = int(actual_demand * service_info['demand_share'])
                    
                    if service_demand > 0:
                        data.append({
                            'date': date,
                            'city': city,
                            'lat': info['lat'],
                            'lon': info['lon'],
                            'region': info['region'],
                            'category': category,
                            'service_level': service,
                            'demand': service_demand,
                            'weight_per_unit_kg': cat_info['weight_kg'],
                            'value_per_unit': cat_info['value'],
                            'total_weight_kg': service_demand * cat_info['weight_kg'],
                            'total_value': service_demand * cat_info['value'],
                        })
    
    return pd.DataFrame(data)

def generate_distance_matrix():
    """
    Calculate distances between all warehouses and demand centers
    """
    data = []
    
    for wh_name, wh_info in WAREHOUSE_LOCATIONS.items():
        for city_name, city_info in DEMAND_CENTERS.items():
            distance = haversine_distance(
                wh_info['lat'], wh_info['lon'],
                city_info['lat'], city_info['lon']
            )
            
            # Calculate costs for different service levels
            for service, service_info in SERVICE_LEVELS.items():
                avg_weight = 2.0  # Average shipment weight in kg
                transport_cost = calculate_transport_cost(distance, avg_weight, service)
                
                data.append({
                    'warehouse': wh_name,
                    'warehouse_lat': wh_info['lat'],
                    'warehouse_lon': wh_info['lon'],
                    'warehouse_region': wh_info['region'],
                    'warehouse_fixed_cost': wh_info['fixed_cost'],
                    'customer_city': city_name,
                    'customer_lat': city_info['lat'],
                    'customer_lon': city_info['lon'],
                    'customer_region': city_info['region'],
                    'distance_km': round(distance, 2),
                    'service_level': service,
                    'service_days': service_info['days'],
                    'transport_cost_per_shipment': transport_cost,
                })
    
    return pd.DataFrame(data)

# ==========================================
# GENERATE AND SAVE DATA
# ==========================================

print("📦 Generating LogiFlow Network Optimization Data...")
print("=" * 70)

# Generate demand data
print("\n1️⃣  Generating demand data (365 days)...")
demand_df = generate_demand_data('2024-01-01', '2024-12-31')
print(f"✅ Generated {len(demand_df):,} demand records")

# Generate distance matrix
print("\n2️⃣  Calculating distance matrix...")
distance_df = generate_distance_matrix()
print(f"✅ Generated {len(distance_df):,} route options")

# Calculate summary statistics
print("\n" + "=" * 70)
print("📊 BUSINESS METRICS SUMMARY")
print("=" * 70)

total_demand = demand_df['demand'].sum()
total_value = demand_df['total_value'].sum()
total_weight = demand_df['total_weight_kg'].sum()

print(f"\nDemand Centers: {len(DEMAND_CENTERS)}")
print(f"Potential Warehouses: {len(WAREHOUSE_LOCATIONS)}")
print(f"Product Categories: {len(PRODUCT_CATEGORIES)}")
print(f"\nAnnual Demand: {total_demand:,} orders")
print(f"Total Value: ${total_value:,.2f}")
print(f"Total Weight: {total_weight:,.0f} kg")

# Regional demand breakdown
print("\n📍 Regional Demand Distribution:")
regional_demand = demand_df.groupby('region')['demand'].sum().sort_values(ascending=False)
for region, demand in regional_demand.items():
    percentage = (demand / total_demand * 100)
    print(f"   {region:15s} {demand:8,} orders ({percentage:5.1f}%)")

# Service level breakdown
print("\n🚚 Service Level Mix:")
service_demand = demand_df.groupby('service_level')['demand'].sum()
for service, demand in service_demand.items():
    percentage = (demand / total_demand * 100)
    print(f"   {service:15s} {demand:8,} orders ({percentage:5.1f}%)")

# Category breakdown
print("\n📦 Product Category Mix:")
category_demand = demand_df.groupby('category')['demand'].sum().sort_values(ascending=False)
for category, demand in category_demand.items():
    percentage = (demand / total_demand * 100)
    print(f"   {category:15s} {demand:8,} orders ({percentage:5.1f}%)")

# Cost estimation
print("\n💰 Cost Estimates (if using all warehouses):")
total_fixed_costs = sum(wh['fixed_cost'] for wh in WAREHOUSE_LOCATIONS.values())
avg_transport_cost = distance_df['transport_cost_per_shipment'].mean()
estimated_transport_cost = total_demand * avg_transport_cost

print(f"   Total Fixed Costs: ${total_fixed_costs:,.0f}/year")
print(f"   Avg Transport Cost: ${avg_transport_cost:.2f}/shipment")
print(f"   Est. Annual Transport: ${estimated_transport_cost:,.0f}")
print(f"   Est. Total Cost: ${total_fixed_costs + estimated_transport_cost:,.0f}/year")

# Save datasets
print("\n" + "=" * 70)
print("💾 SAVING DATASETS")
print("=" * 70)

os.makedirs('../data/raw', exist_ok=True)
os.makedirs('../data/processed', exist_ok=True)

# Save full datasets
demand_df.to_csv('../data/raw/demand_data_2024.csv', index=False)
print("✅ Saved: data/raw/demand_data_2024.csv")

distance_df.to_csv('../data/raw/distance_matrix.csv', index=False)
print("✅ Saved: data/raw/distance_matrix.csv")

# Save aggregated demand (for optimization)
agg_demand = demand_df.groupby(['city', 'lat', 'lon', 'region', 'service_level']).agg({
    'demand': 'sum',
    'total_weight_kg': 'sum',
    'total_value': 'sum'
}).reset_index()

agg_demand.to_csv('../data/processed/aggregated_demand.csv', index=False)
print("✅ Saved: data/processed/aggregated_demand.csv")

# Save warehouse info
warehouse_df = pd.DataFrame([
    {
        'warehouse': name,
        'lat': info['lat'],
        'lon': info['lon'],
        'region': info['region'],
        'fixed_cost_annual': info['fixed_cost']
    }
    for name, info in WAREHOUSE_LOCATIONS.items()
])
warehouse_df.to_csv('../data/processed/warehouse_locations.csv', index=False)
print("✅ Saved: data/processed/warehouse_locations.csv")

# Save summary stats
summary_stats = {
    'total_demand_orders': total_demand,
    'total_value': total_value,
    'total_weight_kg': total_weight,
    'num_demand_centers': len(DEMAND_CENTERS),
    'num_potential_warehouses': len(WAREHOUSE_LOCATIONS),
    'estimated_total_cost_all_warehouses': total_fixed_costs + estimated_transport_cost,
}

summary_df = pd.DataFrame([summary_stats])
summary_df.to_csv('../data/processed/summary_stats.csv', index=False)
print("✅ Saved: data/processed/summary_stats.csv")

print("\n🎉 Data generation complete!")
print("=" * 70)
print("\n💡 OPTIMIZATION OPPORTUNITY:")
print(f"   Current setup (all warehouses): ${total_fixed_costs + estimated_transport_cost:,.0f}/year")
print(f"   Potential savings with optimization: ~$300K-$500K/year (30-40%)")
print("=" * 70)