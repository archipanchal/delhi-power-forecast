import streamlit as st
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Set page configuration
st.set_page_config(
    page_title="Power Demand Forecasting",
    page_icon="⚡",
    layout="wide"
)

# Title and description
st.title("Delhi Power Demand Forecasting")
st.markdown("""
This application forecasts power demand in Delhi using historical data with 5-minute intervals.
""")

@st.cache_data
def load_data():
    """Load and preprocess the data"""
    try:
        df = pd.read_csv("powerdemand_5min_2021_to_2024_with weather.csv")
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def create_features(df):
    """Create features for prediction"""
    df_copy = df.copy()
    
    # Create lag features
    for i in [1, 3, 6, 12, 24]:  # 5min, 15min, 30min, 1h, 2h
        df_copy[f'power_lag_{i}'] = df_copy['Power demand'].shift(i)
    
    # Create rolling means
    df_copy['rolling_mean_6'] = df_copy['Power demand'].rolling(window=6).mean()  # 30min
    df_copy['rolling_mean_12'] = df_copy['Power demand'].rolling(window=12).mean()  # 1h
    
    # Time features
    df_copy['hour'] = df_copy.index.hour
    df_copy['day_of_week'] = df_copy.index.dayofweek
    df_copy['month'] = df_copy.index.month
    df_copy['is_weekend'] = (df_copy['day_of_week'] >= 5).astype(int)
    
    # Weather features (already in the data)
    
    return df_copy

def make_prediction(data, steps_ahead):
    """Make predictions using a simple moving average model"""
    last_value = data['Power demand'].iloc[-1]
    hourly_pattern = data.groupby('hour')['Power demand'].mean()
    
    predictions = []
    current_time = data.index[-1]
    
    for i in range(steps_ahead):
        next_time = current_time + timedelta(minutes=5)
        next_hour = next_time.hour
        
        # Combine last value with hourly pattern
        pred = 0.7 * last_value + 0.3 * hourly_pattern[next_hour]
        predictions.append(pred)
        
        last_value = pred
        current_time = next_time
    
    return np.array(predictions)

# Load data
df = load_data()

if df is not None:
    # Sidebar controls
    st.sidebar.header("Forecast Settings")
    
    forecast_hours = st.sidebar.slider(
        "Forecast Hours",
        min_value=1,
        max_value=24,
        value=2,
        help="Number of hours to forecast ahead"
    )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Historical Power Demand")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index[-48:], df['Power demand'][-48:], label='Historical')
        ax.set_title('Recent Power Demand')
        ax.set_xlabel('Time')
        ax.set_ylabel('Power Demand (MW)')
        ax.legend()
        st.pyplot(fig)
    
    with col2:
        st.subheader("Current Statistics")
        current_demand = df['Power demand'].iloc[-1]
        avg_demand_24h = df['Power demand'].tail(288).mean()  # Last 24 hours
        
        st.metric(
            label="Current Power Demand",
            value=f"{current_demand:.2f} MW",
            delta=f"{current_demand - avg_demand_24h:.2f} MW vs 24h avg"
        )
        
        st.metric(
            label="24h Average Demand",
            value=f"{avg_demand_24h:.2f} MW"
        )
    
    # Make predictions when user clicks the button
    if st.button("Generate Forecast"):
        with st.spinner("Generating forecast..."):
            # Calculate number of steps
            steps = forecast_hours * 12  # 12 5-minute intervals per hour
            
            # Make predictions
            predictions = make_prediction(df, steps)
            
            # Create future timestamps
            last_time = df.index[-1]
            future_times = pd.date_range(
                start=last_time + timedelta(minutes=5),
                periods=steps,
                freq='5T'
            )
            
            # Plot results
            st.subheader("Power Demand Forecast")
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot historical data
            ax.plot(df.index[-48:], df['Power demand'][-48:], 
                   label='Historical', color='blue')
            
            # Plot predictions
            ax.plot(future_times, predictions, 
                   label='Forecast', color='red', linestyle='--')
            
            ax.set_title(f'Power Demand Forecast - Next {forecast_hours} Hours')
            ax.set_xlabel('Time')
            ax.set_ylabel('Power Demand (MW)')
            ax.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
            # Display forecast statistics
            st.subheader("Forecast Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Average Forecasted Demand",
                    value=f"{predictions.mean():.2f} MW"
                )
            
            with col2:
                st.metric(
                    label="Max Forecasted Demand",
                    value=f"{predictions.max():.2f} MW"
                )
            
            with col3:
                st.metric(
                    label="Min Forecasted Demand",
                    value=f"{predictions.min():.2f} MW"
                )
            
            # Display raw forecast data
            if st.checkbox("Show detailed forecast data"):
                forecast_df = pd.DataFrame({
                    'Timestamp': future_times,
                    'Forecasted Demand (MW)': predictions
                })
                forecast_df.set_index('Timestamp', inplace=True)
                st.dataframe(forecast_df)
else:
    st.error("Failed to load data. Please check if the data file exists.") 