# -*- coding: utf-8 -*-
"""
Created on Thu Jun  6 15:05:40 2024

@author: lmspi
"""

import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import cloudpickle
import numpy as np
import matplotlib.pyplot as plt

def read_requirements(file_path):
    with open(file_path, 'r') as file:
        requirements = [line.strip() for line in file if line.strip()]
    return requirements

if __name__ == "__main__":
    # Read requirements.txt
    requirements_file = "requirements.txt"
    requirements = read_requirements(requirements_file)
    print("List of dependencies:")
    for requirement in requirements:
        print(requirement)

    # Load data from pickles
    with open('schiphol_brt_score.pkl', 'rb') as f:
        merged_schiphol_distances = cloudpickle.load(f)

    with open('schiphol_lat_long.pkl', 'rb') as f:
        schiphol_lat_long = cloudpickle.load(f)

    # Ensure that 'schiphol_lat_long' has the necessary structure
    schiphol_lat_long = pd.DataFrame(schiphol_lat_long, columns=['postcode4', 'latitude', 'longitude'])

    # Extract Schiphol's coordinates
    schiphol_coords = schiphol_lat_long[schiphol_lat_long['postcode4'] == 'Schiphol'].iloc[0]
    schiphol_lat = schiphol_coords['latitude']
    schiphol_lon = schiphol_coords['longitude']

    # Merge the distance data with city coordinates
    merged_data = merged_schiphol_distances.merge(
        schiphol_lat_long, 
        left_on='Destination', 
        right_on='postcode4', 
        how='left'
    ).drop(columns=['postcode4'])

    # Streamlit app
    st.title('Postal Zone Pairs BRT Score Visualization')

    city_names = list(schiphol_lat_long['postcode4'].unique())
    city_names.insert(0, "Overall")

    city_name = st.selectbox("Select a Postal Zone (or choose Overall for top 10 Postal zone pairs):", city_names)
    top_n = st.slider("Number of top postal zone pairs to display:", 1, 20, 10)

    # Filter data based on user selection
    if city_name != "Overall":
        filtered_df = merged_data[(merged_data['Origin'] == city_name) | (merged_data['Destination'] == city_name)]
    else:
        filtered_df = merged_data

    top_demand = filtered_df.nlargest(top_n, 'Demand')

    # Create map
    m = folium.Map(location=[schiphol_lat_long['latitude'].mean(), schiphol_lat_long['longitude'].mean()], zoom_start=10)

    marker_cluster = MarkerCluster().add_to(m)

    # Generate colors for the city pairs
    colors = plt.cm.tab10(np.linspace(0, 1, len(top_demand)))

    # Store city labels to prevent duplicates
    added_postal_codes = set()
    lines = []

    for i, row in enumerate(top_demand.itertuples(), start=1):
        if row.Origin == 'Schiphol':
            origin_lat = schiphol_lat
            origin_lon = schiphol_lon
        else:
            continue

        destination = schiphol_lat_long[schiphol_lat_long['postcode4'] == row.Destination].iloc[0]

        # Add markers for origin and destination
        if 'Schiphol' not in added_postal_codes:
            folium.Marker(
                location=[origin_lat, origin_lon],
                popup='Schiphol',
                icon=folium.Icon(color='blue')
            ).add_to(marker_cluster)
            added_postal_codes.add('Schiphol')

        if row.Destination not in added_postal_codes:
            folium.Marker(
                location=[destination['latitude'], destination['longitude']],
                popup=str(row.Destination),
                icon=folium.Icon(color='red')
            ).add_to(marker_cluster)
            added_postal_codes.add(row.Destination)

        color = f'#{int(colors[i % len(colors)][0]*255):02x}{int(colors[i % len(colors)][1]*255):02x}{int(colors[i % len(colors)][2]*255):02x}'

        # Add the polyline for the route
        polyline = folium.PolyLine(
            locations=[[origin_lat, origin_lon], [destination['latitude'], destination['longitude']]],
            color=color,
            weight=5,
            opacity=0.7
        ).add_to(m)
        lines.append((i, polyline))

        # Calculate the midpoint for the label
        midpoint = [(origin_lat + destination['latitude']) / 2, (origin_lon + destination['longitude']) / 2]

        # Add the ranking label at the midpoint
        folium.Marker(
            location=midpoint,
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    background-color: white; 
                    border: 1px solid black; 
                    padding: 2px;
                    border-radius: 50%;
                    text-align: center;
                    font-size: 12px;
                    font-weight: bold;
                    width: 20px;
                    height: 20px;
                    line-height: 16px;  /* Adjusted line-height */
                    ">
                    {i}
                </div>
                """
            )
        ).add_to(m)

    folium_static(m)

    st.markdown("### Postal Zone Pairs with Highest BRT Score")

    # Create a copy of the DataFrame to avoid modifying the original one
    top_demand_copy = top_demand[['Origin', 'Destination', 'Demand']].copy()

    # Rename the 'Demand' column to 'BRT Score'
    top_demand_copy.rename(columns={'Demand': 'BRT Score'}, inplace=True)

    # Convert 'Origin' and 'Destination' to strings to avoid formatting with commas
    top_demand_copy['Origin'] = top_demand_copy['Origin'].astype(str)
    top_demand_copy['Destination'] = top_demand_copy['Destination'].astype(str)

    # Display the table with rounded values
    df_display = top_demand_copy.round(0)
    df_display['BRT Score'] = df_display['BRT Score'].astype(int)
    df_display = df_display.reset_index(drop=True).rename_axis('Ranking').reset_index()
    df_display['Ranking'] += 1
    df_display.set_index('Ranking', inplace=True)
    st.write(df_display)
