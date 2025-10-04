"""
LogiFlow - Network Visualization
Create interactive maps showing warehouse locations and routes
"""

import pandas as pd
import folium
from folium import plugins
import pickle
import json

class NetworkVisualizer:
    """
    Visualize supply chain network on interactive maps
    """
    
    def __init__(self):
        self.solution = None
        self.warehouse_df = None
        self.demand_df = None
        self.distance_df = None
        
    def load_data(self,
                  solution_file='../../models/network_solution.pkl',
                  warehouse_file='../../data/processed/warehouse_locations.csv',
                  demand_file='../../data/processed/aggregated_demand.csv',
                  distance_file='../../data/raw/distance_matrix.csv'):
        """
        Load optimization solution and network data
        """
        print("📊 Loading data for visualization...")
        
        # Load solution
        with open(solution_file, 'rb') as f:
            self.solution = pickle.load(f)
        print(f"✅ Loaded optimization solution")
        
        # Load data
        self.warehouse_df = pd.read_csv(warehouse_file)
        self.demand_df = pd.read_csv(demand_file)
        self.distance_df = pd.read_csv(distance_file)
        print(f"✅ Loaded network data")
        
    def create_network_map(self, output_file='../../dashboards/network_map.html'):
        """
        Create interactive map showing warehouses and routes
        """
        print("\n🗺️  Creating interactive network map...")
        
        # Create base map centered on US
        m = folium.Map(
            location=[39.8283, -98.5795],  # Center of US
            zoom_start=4,
            tiles='OpenStreetMap'
        )
        
        # Get open warehouses
        open_warehouses = self.solution['open_warehouses']
        
        # Add all potential warehouse locations (grayed out if not selected)
        for _, wh in self.warehouse_df.iterrows():
            is_open = wh['warehouse'] in open_warehouses
            
            if is_open:
                color = 'green'
                icon = 'warehouse'
                prefix = 'fa'
                popup_text = f"""
                <b>✅ OPEN WAREHOUSE</b><br>
                <b>{wh['warehouse']}</b><br>
                Region: {wh['region']}<br>
                Fixed Cost: ${wh['fixed_cost_annual']:,.0f}/year
                """
            else:
                color = 'lightgray'
                icon = 'warehouse'
                prefix = 'fa'
                popup_text = f"""
                <b>❌ CLOSED</b><br>
                <b>{wh['warehouse']}</b><br>
                Region: {wh['region']}<br>
                Cost: ${wh['fixed_cost_annual']:,.0f}/year
                """
            
            folium.Marker(
                location=[wh['lat'], wh['lon']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=wh['warehouse'],
                icon=folium.Icon(color=color, icon=icon, prefix=prefix)
            ).add_to(m)
        
        # Add customer locations
        customer_locations = self.demand_df[['city', 'lat', 'lon']].drop_duplicates()
        
        for _, cust in customer_locations.iterrows():
            # Get demand for this customer
            total_demand = self.demand_df[self.demand_df['city'] == cust['city']]['demand'].sum()
            
            popup_text = f"""
            <b>📍 Customer City</b><br>
            <b>{cust['city']}</b><br>
            Annual Demand: {total_demand:,.0f} orders
            """
            
            folium.CircleMarker(
                location=[cust['lat'], cust['lon']],
                radius=5,
                popup=folium.Popup(popup_text, max_width=250),
                tooltip=cust['city'],
                color='blue',
                fill=True,
                fillColor='lightblue',
                fillOpacity=0.6
            ).add_to(m)
        
        # Add routes (lines from warehouses to customers)
        routes_df = self.solution['routes']
        
        for _, route in routes_df.iterrows():
            # Get coordinates
            wh_row = self.warehouse_df[self.warehouse_df['warehouse'] == route['warehouse']].iloc[0]
            cust_row = customer_locations[customer_locations['city'] == route['customer']].iloc[0]
            
            # Line thickness based on shipment volume
            weight = min(route['shipments'] / 5000, 5)  # Scale for visibility
            
            folium.PolyLine(
                locations=[
                    [wh_row['lat'], wh_row['lon']],
                    [cust_row['lat'], cust_row['lon']]
                ],
                color='red',
                weight=weight,
                opacity=0.4,
                popup=f"{route['warehouse']} → {route['customer']}<br>Shipments: {route['shipments']:,.0f}",
                tooltip=f"{route['shipments']:,.0f} shipments"
            ).add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: 180px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p style="margin:0"><b>LogiFlow Network</b></p>
        <p style="margin:5px 0"><span style="color:green">●</span> Open Warehouse</p>
        <p style="margin:5px 0"><span style="color:lightgray">●</span> Closed Warehouse</p>
        <p style="margin:5px 0"><span style="color:lightblue">●</span> Customer City</p>
        <p style="margin:5px 0"><span style="color:red">━</span> Shipping Route</p>
        <p style="margin:5px 0; font-size:12px">Line width = shipment volume</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add title
        title_html = '''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 400px;
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:18px; padding: 10px">
        <b>LogiFlow Optimized Network</b><br>
        <span style="font-size:14px">
        Total Cost: ${:,.0f}/year<br>
        Warehouses: {} | Routes: {}
        </span>
        </div>
        '''.format(
            self.solution['total_cost'],
            self.solution['num_warehouses'],
            len(routes_df)
        )
        m.get_root().html.add_child(folium.Element(title_html))
        
        # Save map
        m.save(output_file)
        print(f"✅ Map saved to: {output_file}")
        print(f"   Open in browser to view!")
        
        return m
    
    def create_comparison_map(self, output_file='../../dashboards/comparison_map.html'):
        """
        Create side-by-side comparison: before vs after optimization
        """
        print("\n🗺️  Creating before/after comparison map...")
        
        # This would show all warehouses vs optimized solution
        # For now, pointing to same visualization
        print("✅ Use network_map.html to see optimized solution")
        
    def generate_summary_stats(self):
        """
        Print summary statistics for the visualization
        """
        print("\n" + "=" * 70)
        print("📊 NETWORK VISUALIZATION SUMMARY")
        print("=" * 70)
        
        routes_df = self.solution['routes']
        
        print(f"\n🏭 Warehouse Configuration:")
        print(f"   Open Warehouses: {self.solution['num_warehouses']}")
        print(f"   Locations: {', '.join(self.solution['open_warehouses'])}")
        
        print(f"\n📦 Routing Statistics:")
        print(f"   Total Routes: {len(routes_df)}")
        print(f"   Total Shipments: {routes_df['shipments'].sum():,.0f}")
        print(f"   Avg Shipments/Route: {routes_df['shipments'].mean():,.0f}")
        
        print(f"\n💰 Cost Breakdown:")
        print(f"   Fixed Costs:     ${self.solution['fixed_cost']:,.0f}/year")
        print(f"   Variable Costs:  ${self.solution['variable_cost']:,.0f}/year")
        print(f"   TOTAL:           ${self.solution['total_cost']:,.0f}/year")
        
        # Top routes by volume
        print(f"\n🚚 Top 5 Routes by Volume:")
        top_routes = routes_df.nlargest(5, 'shipments')
        for idx, route in top_routes.iterrows():
            print(f"   {route['warehouse']:20s} → {route['customer']:15s}  {route['shipments']:8,.0f} shipments")


# ==========================================
# MAIN VISUALIZATION SCRIPT
# ==========================================

if __name__ == "__main__":
    print("\n🗺️  LogiFlow - Network Visualization")
    print("=" * 70)
    
    # Initialize visualizer
    viz = NetworkVisualizer()
    
    # Load data
    viz.load_data()
    
    # Generate summary
    viz.generate_summary_stats()
    
    # Create interactive map
    viz.create_network_map()
    
    print("\n" + "=" * 70)
    print("🎉 Visualization Complete!")
    print("=" * 70)
    print("\n💡 Next step: Open 'dashboards/network_map.html' in your browser!")