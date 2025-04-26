import streamlit as st

# Set page configuration must be the first Streamlit command
st.set_page_config(
    page_title="Delhi Power Demand Analysis",
    page_icon="⚡",
    layout="wide"
)

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import calendar
import matplotlib.pyplot as plt

# Handle package imports with error handling
try:
    from sklearn.preprocessing import MinMaxScaler
except ImportError:
    st.error("Error: scikit-learn is not installed. Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
    from sklearn.preprocessing import MinMaxScaler

try:
    import seaborn as sns
except ImportError:
    st.error("Error: seaborn is not installed. Installing required packages...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "seaborn"])
    import seaborn as sns

import joblib

# Custom styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stPlotlyChart {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 1rem;
    }
    h1, h2, h3 {
        color: #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("Delhi Power Demand Analysis & Forecast")
st.markdown("""
This application provides comprehensive power demand analysis and forecasting for Delhi.
Historical data analysis is combined with future predictions to offer valuable insights.
""")

@st.cache_data
def load_data():
    """Load and preprocess the data"""
    try:
        # Try to load the full dataset first
        file_path = "powerdemand_5min_2021_to_2024_with weather.csv"
        if not os.path.exists(file_path):
            # If full dataset is not available, try loading sample data
            file_path = "sample_power_demand.csv"
            if not os.path.exists(file_path):
                st.error("No data file found. Please run create_sample_data.py first to generate sample data.")
                return None
            st.info("Using sample data for demonstration. For full functionality, please use the complete dataset.")
            
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.info("Please check if the data file is properly formatted and accessible.")
        return None

def filter_forecast_data(forecast_df, selected_month=None, selected_week=None, selected_date=None):
    """Filter forecast data based on selected periods"""
    filtered_data = forecast_df.copy()
    
    if selected_month:
        filtered_data = filtered_data[filtered_data.index.month == selected_month]
    
    if selected_week:
        filtered_data = filtered_data[filtered_data.index.isocalendar().week == selected_week]
    
    if selected_date:
        selected_date = pd.to_datetime(selected_date)
        filtered_data = filtered_data[filtered_data.index.date == selected_date.date()]
    
    return filtered_data

def predict_2025(data, prediction_type):
    """Make predictions for 2025"""
    # Create timestamps for 2025 first to know the exact length needed
    dates = pd.date_range(start='2025-01-01', end='2025-12-31 23:00:00', freq='h')
    total_hours = len(dates)
    
    # Calculate base patterns from historical data
    if prediction_type == "Monthly":
        base_pattern = data.groupby([data.index.month, data.index.hour])['Power demand'].mean().unstack()
        predictions = []
        
        # Calculate predictions for each month
        for month in range(1, 13):
            # Get number of hours in this month
            month_dates = dates[dates.month == month]
            month_hours = len(month_dates)
            
            # Get the monthly pattern and repeat it for all days in the month
            month_pattern = np.tile(base_pattern.loc[month].values, (month_hours // 24 + 1))[:month_hours]
            # Add yearly growth and variation
            month_pattern = month_pattern * 1.05  # 5% annual increase
            variation = np.random.uniform(0.98, 1.02, size=len(month_pattern))
            predictions.extend(month_pattern * variation)
    
    else:  # Hourly (base pattern)
        base_pattern = data.groupby(data.index.hour)['Power demand'].mean()
        predictions = []
        
        # Calculate predictions hour by hour
        for hour in range(total_hours):
            hour_of_day = hour % 24
            pred = base_pattern[hour_of_day] * 1.05  # 5% annual increase
            variation = np.random.uniform(0.98, 1.02)  # ±2% random variation
            predictions.append(pred * variation)

    # Ensure predictions match the exact length needed
    predictions = np.array(predictions)[:total_hours]
    
    # Create DataFrame with predictions
    forecast_df = pd.DataFrame({
        'Power demand': predictions
    }, index=dates)
    
    return forecast_df

# Load data
df = load_data()

if df is not None:
    # Sidebar controls
    st.sidebar.header("Forecast Settings")
    
    # Month selection
    selected_month = st.sidebar.selectbox(
        "Select Month (2025)",
        [(i, calendar.month_name[i]) for i in range(1, 13)],
        format_func=lambda x: x[1]
    )[0]
    
    # Week selection with dates
    weeks_in_month = pd.date_range(
        start=f'2025-{selected_month}-01',
        end=pd.Timestamp(f'2025-{selected_month}-01') + pd.offsets.MonthEnd(),
        freq='W'
    )
    
    # Create week options with date ranges
    week_options = []
    for week_start in weeks_in_month:
        week_end = week_start + pd.Timedelta(days=6)
        week_num = week_start.isocalendar().week
        week_label = f"Week {week_num} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d')})"
        week_options.append((week_num, week_label))
    
    selected_week = st.sidebar.selectbox(
        "Select Week",
        options=week_options,
        format_func=lambda x: x[1]
    )[0]
    
    # Date selection
    dates_in_month = pd.date_range(
        start=f'2025-{selected_month}-01',
        end=pd.Timestamp(f'2025-{selected_month}-01') + pd.offsets.MonthEnd(),
        freq='D'
    )
    selected_date = st.sidebar.selectbox(
        "Select Date",
        dates_in_month,
        format_func=lambda x: x.strftime('%Y-%m-%d')
    )
    
    # Generate 2025 predictions when user clicks the button
    if st.button("Generate 2025 Forecast"):
        with st.spinner("Generating forecast for 2025..."):
            # Get predictions for 2025
            forecast_2025 = predict_2025(df, "Hourly")  # We'll use hourly as base
            
            # Filter data based on selections
            monthly_data = filter_forecast_data(forecast_2025, selected_month=selected_month)
            weekly_data = filter_forecast_data(forecast_2025, selected_week=selected_week)
            daily_data = filter_forecast_data(forecast_2025, selected_date=selected_date)
            
            # Create main display areas
            st.header("Power Demand Analysis")
            
            # Create two columns for Historical and Forecast
            hist_col, forecast_col = st.columns(2)
            
            with hist_col:
                st.subheader("Historical Data Analysis")
                
                # Create tabs for historical data
                hist_tab1, hist_tab2, hist_tab3 = st.tabs(["Monthly Analysis", "Weekly Analysis", "Daily Analysis"])
                
                with hist_tab1:
                    st.markdown(f"### Monthly Historical Data - {calendar.month_name[selected_month]}")
                    
                    # Statistics
                    monthly_hist = df[df.index.month == selected_month]
                    st.markdown(f"""
                    #### Key Statistics
                    - **Average**: {monthly_hist['Power demand'].mean():.2f} MW
                    - **Maximum**: {monthly_hist['Power demand'].max():.2f} MW
                    - **Minimum**: {monthly_hist['Power demand'].min():.2f} MW
                    """)
                    
                    # Plot
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(monthly_hist.index, monthly_hist['Power demand'], label='Historical')
                    ax.set_title(f'Historical Power Demand - {calendar.month_name[selected_month]}')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Power Demand (MW)')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Data table
                    st.markdown("#### Detailed Data")
                    st.dataframe(monthly_hist.round(2))
                
                with hist_tab2:
                    st.markdown(f"### Weekly Historical Data - Week {selected_week}")
                    
                    # Statistics
                    weekly_hist = df[df.index.isocalendar().week == selected_week]
                    st.markdown(f"""
                    #### Key Statistics
                    - **Average**: {weekly_hist['Power demand'].mean():.2f} MW
                    - **Maximum**: {weekly_hist['Power demand'].max():.2f} MW
                    - **Minimum**: {weekly_hist['Power demand'].min():.2f} MW
                    """)
                    
                    # Plot
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(weekly_hist.index, weekly_hist['Power demand'], label='Historical')
                    ax.set_title(f'Historical Power Demand - Week {selected_week}')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Power Demand (MW)')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Data table
                    st.markdown("#### Detailed Data")
                    st.dataframe(weekly_hist.round(2))
                
                with hist_tab3:
                    st.markdown(f"### Daily Historical Data - {selected_date.strftime('%A, %B %d')}")
                    
                    # Statistics
                    daily_hist = df[
                        (df.index.month == selected_date.month) & 
                        (df.index.day == selected_date.day)
                    ]
                    st.markdown(f"""
                    #### Key Statistics
                    - **Average**: {daily_hist['Power demand'].mean():.2f} MW
                    - **Maximum**: {daily_hist['Power demand'].max():.2f} MW
                    - **Minimum**: {daily_hist['Power demand'].min():.2f} MW
                    """)
                    
                    # Plot
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(daily_hist.index, daily_hist['Power demand'], label='Historical')
                    ax.set_title(f'Historical Power Demand - {selected_date.strftime("%A, %B %d")}')
                    ax.set_xlabel('Hour')
                    ax.set_ylabel('Power Demand (MW)')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Data table
                    st.markdown("#### Detailed Data")
                    st.dataframe(daily_hist.round(2))
            
            with forecast_col:
                st.subheader("2025 Forecast Analysis")
                
                # Create tabs for forecast data
                forecast_tab1, forecast_tab2, forecast_tab3 = st.tabs(["Monthly Analysis", "Weekly Analysis", "Daily Analysis"])
                
                with forecast_tab1:
                    st.markdown(f"### Monthly Forecast - {calendar.month_name[selected_month]} 2025")
                    
                    # Statistics
                    monthly_forecast = monthly_data
                    st.markdown(f"""
                    #### Key Statistics
                    - **Average**: {monthly_forecast['Power demand'].mean():.2f} MW
                    - **Maximum**: {monthly_forecast['Power demand'].max():.2f} MW
                    - **Minimum**: {monthly_forecast['Power demand'].min():.2f} MW
                    """)
                    
                    # Plot
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(monthly_forecast.index, monthly_forecast['Power demand'], label='Forecast', color='orange')
                    ax.set_title(f'Power Demand Forecast - {calendar.month_name[selected_month]} 2025')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Power Demand (MW)')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Data table
                    st.markdown("#### Detailed Data")
                    st.dataframe(monthly_forecast.round(2))
                
                with forecast_tab2:
                    st.markdown(f"### Weekly Forecast - Week {selected_week}, 2025")
                    
                    # Statistics
                    weekly_forecast = weekly_data
                    st.markdown(f"""
                    #### Key Statistics
                    - **Average**: {weekly_forecast['Power demand'].mean():.2f} MW
                    - **Maximum**: {weekly_forecast['Power demand'].max():.2f} MW
                    - **Minimum**: {weekly_forecast['Power demand'].min():.2f} MW
                    """)
                    
                    # Plot
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(weekly_forecast.index, weekly_forecast['Power demand'], label='Forecast', color='orange')
                    ax.set_title(f'Power Demand Forecast - Week {selected_week}, 2025')
                    ax.set_xlabel('Date')
                    ax.set_ylabel('Power Demand (MW)')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Data table
                    st.markdown("#### Detailed Data")
                    st.dataframe(weekly_forecast.round(2))
                
                with forecast_tab3:
                    st.markdown(f"### Daily Forecast - {selected_date.strftime('%A, %B %d')}, 2025")
                    
                    # Statistics
                    daily_forecast = daily_data
                    st.markdown(f"""
                    #### Key Statistics
                    - **Average**: {daily_forecast['Power demand'].mean():.2f} MW
                    - **Maximum**: {daily_forecast['Power demand'].max():.2f} MW
                    - **Minimum**: {daily_forecast['Power demand'].min():.2f} MW
                    """)
                    
                    # Plot
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(daily_forecast.index, daily_forecast['Power demand'], label='Forecast', color='orange')
                    ax.set_title(f'Power Demand Forecast - {selected_date.strftime("%A, %B %d, %Y")}')
                    ax.set_xlabel('Hour')
                    ax.set_ylabel('Power Demand (MW)')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Data table
                    st.markdown("#### Detailed Data")
                    st.dataframe(daily_forecast.round(2))
            
            # Download section
            st.header("Download Data")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Historical Data")
                # Monthly download
                hist_monthly_csv = monthly_hist.to_csv()
                st.download_button(
                    label="Download Monthly Historical Data",
                    data=hist_monthly_csv,
                    file_name=f"historical_power_demand_{selected_month}.csv",
                    mime="text/csv"
                )
                # Weekly download
                hist_weekly_csv = weekly_hist.to_csv()
                st.download_button(
                    label="Download Weekly Historical Data",
                    data=hist_weekly_csv,
                    file_name=f"historical_power_demand_week_{selected_week}.csv",
                    mime="text/csv"
                )
                # Daily download
                hist_daily_csv = daily_hist.to_csv()
                st.download_button(
                    label="Download Daily Historical Data",
                    data=hist_daily_csv,
                    file_name=f"historical_power_demand_{selected_date.strftime('%Y-%m-%d')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                st.subheader("Forecast Data")
                # Monthly download
                forecast_monthly_csv = monthly_forecast.to_csv()
                st.download_button(
                    label="Download Monthly Forecast Data",
                    data=forecast_monthly_csv,
                    file_name=f"forecast_power_demand_{selected_month}.csv",
                    mime="text/csv"
                )
                # Weekly download
                forecast_weekly_csv = weekly_forecast.to_csv()
                st.download_button(
                    label="Download Weekly Forecast Data",
                    data=forecast_weekly_csv,
                    file_name=f"forecast_power_demand_week_{selected_week}.csv",
                    mime="text/csv"
                )
                # Daily download
                forecast_daily_csv = daily_forecast.to_csv()
                st.download_button(
                    label="Download Daily Forecast Data",
                    data=forecast_daily_csv,
                    file_name=f"forecast_power_demand_{selected_date.strftime('%Y-%m-%d')}.csv",
                    mime="text/csv"
                )
                
            # Footer with notes
            st.markdown("""
            ---
            ### Notes
            - Historical data shows actual power demand patterns from 2021-2024
            - Forecast data includes 5% annual growth projection for 2025
            - Both analyses maintain consistent daily and seasonal patterns
            - Download options available for detailed data analysis
            """)
else:
    st.error("Failed to load data. Please check if the data file exists.") 