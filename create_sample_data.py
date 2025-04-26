import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create sample data
print("Creating sample data...")

# Generate timestamps for 7 days with 5-minute intervals
start_date = datetime(2024, 1, 1)
dates = [start_date + timedelta(minutes=5*i) for i in range(7*24*12)]  # 7 days * 24 hours * 12 intervals

# Generate synthetic power demand data
np.random.seed(42)
base_demand = 2000  # Base power demand in MW
hourly_pattern = np.sin(np.linspace(0, 2*np.pi, 24)) * 500 + base_demand  # Daily pattern

# Create the dataframe
data = []
for date in dates:
    hour = date.hour
    base = hourly_pattern[hour]
    
    # Add some random variation
    demand = base + np.random.normal(0, 100)
    
    # Add weather data
    temperature = 20 + np.sin(np.pi * hour / 12) * 5 + np.random.normal(0, 2)
    humidity = 60 + np.random.normal(0, 10)
    
    data.append({
        'datetime': date,
        'Power demand': max(0, demand),
        'Temperature': temperature,
        'Humidity': humidity
    })

df = pd.DataFrame(data)

# Save to CSV
print("Saving sample data...")
df.to_csv('sample_power_demand.csv', index=False)
print("Sample data created successfully!")
print(f"Shape of sample data: {df.shape}")
print("\nFirst few rows:")
print(df.head()) 