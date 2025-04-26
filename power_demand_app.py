import streamlit as st
import pandas as pd
import numpy as np
from tensorflow import keras # type: ignore
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
This application predicts power demand in Delhi using an LSTM neural network.
The model is trained on historical data with 5-minute intervals.
""")

@st.cache_resource
def load_model_and_scaler():
    """Load the trained model and scaler"""
    try:
        model = keras.models.load_model('lstm_model.h5')
        scaler = joblib.load('scaler.pkl')
        return model, scaler
    except Exception as e:
        st.error(f"Error loading model or scaler: {str(e)}")
        return None, None

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
    for i in [1, 3, 6]:
        df_copy[f'power_lag_{i}'] = df_copy['Power demand'].shift(i)
    
    # Create rolling means
    df_copy['rolling_mean_3'] = df_copy['Power demand'].rolling(window=3).mean()
    df_copy['rolling_mean_6'] = df_copy['Power demand'].rolling(window=6).mean()
    
    # Time features
    df_copy['hour'] = df_copy.index.hour
    df_copy['day_of_week'] = df_copy.index.dayofweek
    df_copy['month'] = df_copy.index.month
    df_copy['is_weekend'] = (df_copy['day_of_week'] >= 5).astype(int)
    
    return df_copy

def predict_future(model, last_sequence, scaler, n_steps, df_columns):
    """Make future predictions"""
    future_predictions = []
    current_sequence = last_sequence.copy()
    
    for _ in range(n_steps):
        # Reshape sequence for prediction
        current_sequence_reshaped = current_sequence.reshape(1, 30, -1)
        next_pred = model.predict(current_sequence_reshaped, verbose=0)
        future_predictions.append(next_pred[0, 0])
        
        # Update sequence for next prediction
        current_sequence = np.roll(current_sequence, -1, axis=0)
        current_sequence[-1] = current_sequence[-2]  # Copy previous values for other features
        current_sequence[-1, df_columns.get_loc('Power demand')] = next_pred[0, 0]
    
    return np.array(future_predictions)

# Load data first
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
    
    # Load model and scaler only when needed
    if st.button("Generate Forecast"):
        model, scaler = load_model_and_scaler()
        
        if model is not None and scaler is not None:
            with st.spinner("Generating forecast..."):
                # Prepare data for prediction
                df_processed = create_features(df)
                df_scaled = pd.DataFrame(
                    scaler.transform(df_processed),
                    columns=df_processed.columns,
                    index=df_processed.index
                )
                
                # Get last sequence for prediction
                last_sequence = df_scaled.values[-30:]
                
                # Make predictions
                steps = forecast_hours * 12  # 12 5-minute intervals per hour
                predictions = predict_future(model, last_sequence, scaler, steps, df_scaled.columns)
                
                # Create future timestamps
                last_time = df.index[-1]
                future_times = pd.date_range(
                    start=last_time + timedelta(minutes=5),
                    periods=steps,
                    freq='5T'
                )
                
                # Inverse transform predictions
                predictions_array = np.zeros((len(predictions), df_processed.shape[1]))
                predictions_array[:, df_processed.columns.get_loc('Power demand')] = predictions
                predictions_original = scaler.inverse_transform(predictions_array)[:, df_processed.columns.get_loc('Power demand')]
                
                # Plot results
                st.subheader("Power Demand Forecast")
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # Plot historical data
                ax.plot(df.index[-48:], df['Power demand'][-48:], 
                       label='Historical', color='blue')
                
                # Plot predictions
                ax.plot(future_times, predictions_original, 
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
                        value=f"{predictions_original.mean():.2f} MW"
                    )
                
                with col2:
                    st.metric(
                        label="Max Forecasted Demand",
                        value=f"{predictions_original.max():.2f} MW"
                    )
                
                with col3:
                    st.metric(
                        label="Min Forecasted Demand",
                        value=f"{predictions_original.min():.2f} MW"
                    )
                
                # Display raw forecast data
                if st.checkbox("Show detailed forecast data"):
                    forecast_df = pd.DataFrame({
                        'Timestamp': future_times,
                        'Forecasted Demand (MW)': predictions_original
                    })
                    forecast_df.set_index('Timestamp', inplace=True)
                    st.dataframe(forecast_df)
        else:
            st.error("Failed to load model or scaler. Please check if the files exist.")
else:
    st.error("Failed to load data. Please check if the data file exists.") 