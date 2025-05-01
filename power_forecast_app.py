#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Delhi Power Consumption Forecast Application
A Streamlit web application for analyzing and forecasting electricity demand in Delhi.
"""

import os
import sys
import time
import datetime
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from dotenv import load_dotenv
import threading
import re

# Load environment variables from .env file
load_dotenv()

# Try to import our custom logging module
try:
    from logging_system import setup_streamlit_logging
    logger = setup_streamlit_logging()
except ImportError:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger('streamlit_app')
    logger.info("Custom logging module not found, using basic logging")

# Ensure data directory exists
data_dir = Path('data')
data_dir.mkdir(exist_ok=True)

# Global variables for sharing between threads
_data_loading_thread = None
_data_loading_complete = False
_data = None
_forecasts = None

def preload_data_thread():
    """Background thread to preload data"""
    global _data_loading_complete, _data, _forecasts
    
    data_file = data_dir / 'sample_power_demand.csv'
    forecast_file = data_dir / 'sample_forecast.csv'
    
    # Load from files if they exist
    if data_file.exists() and forecast_file.exists():
        try:
            logger.info("Background thread: Loading data from files")
            _data = pd.read_csv(data_file, parse_dates=['timestamp'])
            _forecasts = pd.read_csv(forecast_file, parse_dates=['timestamp'])
            logger.info("Background thread: Data loading complete")
        except Exception as e:
            logger.error(f"Background thread: Error loading data: {str(e)}")
    
    _data_loading_complete = True

# Start background data loading immediately
_data_loading_thread = threading.Thread(target=preload_data_thread, daemon=True)
_data_loading_thread.start()

# Page configuration
st.set_page_config(
    page_title="Delhi Power Consumption Forecast",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to enhance the UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-bottom: 1rem;
    }
    .insight-box {
        background-color: #F3F3F3;
        border-radius: 5px;
        padding: 10px;
        border-left: 5px solid #1E88E5;
    }
    .stButton>button {
        background-color: #1E88E5;
        color: white;
    }
    .stProgress .st-bs {
        background-color: #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

class PowerForecastApp:
    """Main Streamlit application for power demand forecasting"""
    
    def __init__(self):
        """Initialize the application"""
        self.data = None
        self.model = None
        self.forecasts = None
        
        # Initialize session state for persistent UI state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None
        if 'view' not in st.session_state:
            st.session_state.view = "monthly"
        if 'selected_date' not in st.session_state:
            st.session_state.selected_date = datetime.date.today()
        if 'data_loaded' not in st.session_state:
            st.session_state.data_loaded = False
            
        # Check if background thread has completed loading
        global _data_loading_complete, _data, _forecasts
        if _data_loading_complete and _data is not None and _forecasts is not None:
            logger.info("Using preloaded data from background thread")
            self.data = _data
            self.forecasts = _forecasts
            st.session_state.data_loaded = True
        else:
            # Fallback to file checking if thread hasn't completed
            data_file = data_dir / 'sample_power_demand.csv'
            forecast_file = data_dir / 'sample_forecast.csv'
            
            # Preload only if both files exist
            if data_file.exists() and forecast_file.exists():
                logger.info("Preloading data during initialization (thread not complete)")
                try:
                    self.data = pd.read_csv(data_file, parse_dates=['timestamp'])
                    self.forecasts = pd.read_csv(forecast_file, parse_dates=['timestamp'])
                    st.session_state.data_loaded = True
                    logger.info("Data preloaded successfully")
                except Exception as e:
                    logger.error(f"Error preloading data: {str(e)}")
        
        # Log application start
        logger.info("Application started")
    
    def load_sample_data(self):
        """Load sample power demand data for demonstration"""
        # Check if pre-generated data exists
        data_file = data_dir / 'sample_power_demand.csv'
        if data_file.exists():
            logger.info("Loading pre-generated sample data")
            start_time = time.time()
            self.data = pd.read_csv(data_file, parse_dates=['timestamp'])
            logger.info(f"Data loaded in {time.time() - start_time:.2f} seconds")
            return self.data
            
        logger.info("Generating synthetic sample data")
        start_time = time.time()
        
        # In a real application, this would load from a database or files
        # For now, generate synthetic data
        
        start_date = datetime.datetime(2021, 1, 1)
        end_date = datetime.datetime(2024, 6, 30)
        date_range = pd.date_range(start=start_date, end=end_date, freq='5min')
        
        # Generate synthetic hourly pattern with morning and evening peaks
        hourly_pattern = np.sin(np.linspace(0, 2*np.pi, 24)) * 0.5 + 0.5
        hourly_pattern[7:9] = hourly_pattern[7:9] * 1.5  # Morning peak
        hourly_pattern[18:21] = hourly_pattern[18:21] * 2  # Evening peak
        
        # Generate synthetic daily pattern with weekday/weekend differences
        daily_pattern = np.ones(7)
        daily_pattern[5:7] = 0.8  # Weekend reduction
        
        # Generate synthetic seasonal pattern with summer peaks
        monthly_pattern = 1 + 0.3 * np.sin(np.linspace(0, 2*np.pi, 12))
        
        # Generate synthetic yearly growth trend
        yearly_growth = np.linspace(1, 1.15, len(date_range))
        
        # Generate base demand values with patterns
        logger.info("Generating demand values")
        demand = []
        for dt in date_range:
            hour_factor = hourly_pattern[dt.hour]
            day_factor = daily_pattern[dt.weekday()]
            month_factor = monthly_pattern[dt.month-1]
            
            # Base demand around 3000-4000 MW
            base_demand = 3500
            
            # Apply patterns and add noise
            demand_value = (
                base_demand * 
                hour_factor * 
                day_factor * 
                month_factor * 
                yearly_growth[len(demand)]
            )
            
            # Add random noise (2% variation)
            noise = np.random.normal(0, 0.02 * demand_value)
            demand_value += noise
            
            demand.append(max(0, demand_value))
        
        # Create DataFrame
        self.data = pd.DataFrame({
            'timestamp': date_range,
            'demand_mw': demand
        })
        
        # Add datetime components for easier filtering
        logger.info("Adding datetime components")
        self.data['date'] = self.data['timestamp'].dt.date
        self.data['hour'] = self.data['timestamp'].dt.hour
        self.data['day'] = self.data['timestamp'].dt.day
        self.data['month'] = self.data['timestamp'].dt.month
        self.data['year'] = self.data['timestamp'].dt.year
        self.data['day_of_week'] = self.data['timestamp'].dt.dayofweek
        
        # Save generated data for future use
        logger.info("Saving generated data to file")
        data_dir.mkdir(exist_ok=True)
        self.data.to_csv(data_file, index=False)
        
        logger.info(f"Data generation completed in {time.time() - start_time:.2f} seconds")
        return self.data
    
    def generate_sample_forecast(self):
        """Generate sample forecasts for demonstration"""
        if self.data is None:
            self.load_sample_data()
            
        # Check if pre-generated forecasts exist
        forecast_file = data_dir / 'sample_forecast.csv'
        if forecast_file.exists():
            logger.info("Loading pre-generated forecasts")
            start_time = time.time()
            self.forecasts = pd.read_csv(forecast_file, parse_dates=['timestamp'])
            logger.info(f"Forecasts loaded in {time.time() - start_time:.2f} seconds")
            return self.forecasts
        
        logger.info("Generating sample forecasts")
        start_time = time.time()
        
        # Create a future date range for forecast
        last_date = self.data['timestamp'].max()
        forecast_start = last_date + datetime.timedelta(minutes=5)
        forecast_end = forecast_start + datetime.timedelta(days=30)
        forecast_range = pd.date_range(start=forecast_start, end=forecast_end, freq='5min')
        
        # Copy patterns from historical data with slight modifications
        # In a real app, this would use an actual ML model
        
        forecasts = []
        for dt in forecast_range:
            # Find a similar day in historical data
            historical_dt = dt - datetime.timedelta(days=365)
            closest_idx = (self.data['timestamp'] - historical_dt).abs().idxmin()
            
            # Get historical value
            historical_value = self.data.loc[closest_idx, 'demand_mw']
            
            # Apply slight growth factor and add noise
            forecast_value = historical_value * 1.05
            noise = np.random.normal(0, 0.05 * forecast_value)
            forecast_value += noise
            
            forecasts.append({
                'timestamp': dt,
                'demand_mw': max(0, forecast_value),
                'date': dt.date(),
                'hour': dt.hour,
                'day': dt.day,
                'month': dt.month,
                'year': dt.year,
                'day_of_week': dt.dayofweek
            })
        
        self.forecasts = pd.DataFrame(forecasts)
        
        # Save generated forecasts for future use
        logger.info("Saving generated forecasts to file")
        data_dir.mkdir(exist_ok=True)
        self.forecasts.to_csv(forecast_file, index=False)
        
        logger.info(f"Forecast generation completed in {time.time() - start_time:.2f} seconds")
        return self.forecasts
    
    def validate_email(self, email):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def validate_mobile(self, mobile):
        """Validate mobile number format"""
        # Accept formats like +91 1234567890, 1234567890, etc.
        mobile_pattern = r'^(\+\d{1,3}\s?)?\d{10}$'
        return bool(re.match(mobile_pattern, mobile))
    
    def authenticate_user(self):
        """Handle user authentication"""
        # Start data loading in background while user is on login screen
        if not st.session_state.data_loaded and self.data is None:
            info_placeholder = st.empty()
            info_placeholder.info("Preparing application data in the background...")
            self.load_sample_data()
            self.generate_sample_forecast()
            st.session_state.data_loaded = True
            info_placeholder.empty()
        
        # This is a placeholder - in a real app, implement proper authentication
        st.sidebar.title("User Authentication")
        
        auth_type = st.sidebar.radio("Authentication Method", ["Guest Access", "Google Sign-In", "Email Verification"])
        
        if auth_type == "Guest Access":
            name = st.sidebar.text_input("Your Name (Optional)")
            login_button = st.sidebar.button("Continue as Guest")
            
            if login_button:
                logger.info(f"Guest login: {name if name else 'Anonymous'}")
                st.session_state.authenticated = True
                st.session_state.user_info = {"name": name if name else "Guest", "role": "guest"}
                return True
                
        elif auth_type == "Google Sign-In":
            st.sidebar.info("In a production environment, this would integrate with Google OAuth.")
            email = st.sidebar.text_input("Email")
            password = st.sidebar.text_input("Password", type="password")
            login_button = st.sidebar.button("Sign In")
            
            if login_button:
                if not email or not password:
                    st.sidebar.error("Please enter both email and password")
                    return False
                
                if not self.validate_email(email):
                    st.sidebar.error("Please enter a valid email address")
                    return False
                
                # In a real app, validate password strength as well
                
                # This is just a simulation
                logger.info(f"Simulated Google login: {email}")
                st.session_state.authenticated = True
                st.session_state.user_info = {"name": email.split('@')[0], "email": email, "role": "user"}
                return True
        
        elif auth_type == "Email Verification":
            email = st.sidebar.text_input("Email Address")
            mobile = st.sidebar.text_input("Mobile Number")
            
            send_code = st.sidebar.button("Send Verification Code")
            
            if send_code:
                if not email or not mobile:
                    st.sidebar.warning("Please enter both email and mobile number")
                    return False
                
                # Validate inputs
                email_valid = self.validate_email(email)
                mobile_valid = self.validate_mobile(mobile)
                
                if not email_valid:
                    st.sidebar.error("Please enter a valid email address")
                    return False
                
                if not mobile_valid:
                    st.sidebar.error("Please enter a valid 10-digit mobile number")
                    return False
                
                # In a real app, this would send an actual email and SMS
                st.session_state.verification_code = "123456"  # Demo code
                st.sidebar.success("Verification code sent! (Demo: 123456)")
            
            verification_code = st.sidebar.text_input("Verification Code")
            verify_button = st.sidebar.button("Verify & Login")
            
            if verify_button:
                if not verification_code:
                    st.sidebar.error("Please enter the verification code")
                    return False
                
                if verification_code == st.session_state.get("verification_code", ""):
                    logger.info(f"Email verification login: {email}")
                    st.session_state.authenticated = True
                    st.session_state.user_info = {"name": email.split('@')[0], "email": email, "mobile": mobile, "role": "verified_user"}
                    return True
                else:
                    st.sidebar.error("Invalid verification code")
        
        return False
    
    def display_header(self):
        """Display application header"""
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            st.markdown("<h1 class='main-header'>Delhi Power Consumption Forecast</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center'>Analyze historical power demand patterns and forecast future consumption</p>", unsafe_allow_html=True)
    
    def display_sidebar(self):
        """Display sidebar with controls"""
        st.sidebar.title("Controls")
        
        # View selection
        st.sidebar.subheader("View Options")
        view = st.sidebar.radio(
            "Select View",
            ["Monthly", "Weekly", "Daily", "Hourly"],
            index=0,
            key="view_selection"
        )
        st.session_state.view = view.lower()
        
        # Date selection
        st.sidebar.subheader("Date Selection")
        if st.session_state.view == "monthly":
            year = st.sidebar.selectbox("Year", options=[2021, 2022, 2023, 2024, 2025], index=3)
            month = st.sidebar.selectbox("Month", options=range(1, 13), index=datetime.date.today().month - 1)
            st.session_state.selected_date = datetime.date(year, month, 1)
        elif st.session_state.view == "weekly":
            selected_date = st.sidebar.date_input(
                "Select Week Starting",
                value=st.session_state.selected_date,
                min_value=datetime.date(2021, 1, 1),
                max_value=datetime.date(2025, 12, 31)
            )
            # Adjust to start of week (Monday)
            weekday = selected_date.weekday()
            st.session_state.selected_date = selected_date - datetime.timedelta(days=weekday)
        elif st.session_state.view == "daily":
            st.session_state.selected_date = st.sidebar.date_input(
                "Select Date",
                value=st.session_state.selected_date,
                min_value=datetime.date(2021, 1, 1),
                max_value=datetime.date(2025, 12, 31)
            )
        elif st.session_state.view == "hourly":
            selected_date = st.sidebar.date_input(
                "Select Date",
                value=st.session_state.selected_date,
                min_value=datetime.date(2021, 1, 1),
                max_value=datetime.date(2025, 12, 31)
            )
            hour = st.sidebar.slider("Hour", 0, 23, 12)
            st.session_state.selected_date = selected_date
            st.session_state.selected_hour = hour
        
        # Additional filters
        st.sidebar.subheader("Filters")
        st.sidebar.checkbox("Show Historical Data", value=True, key="show_historical")
        st.sidebar.checkbox("Show Forecast", value=True, key="show_forecast")
        
        if st.sidebar.button("Generate Report"):
            # In a real app, this would generate a downloadable report
            st.sidebar.success("Report generated! (Demo)")
    
    def filter_data_by_view(self, df, forecast_df):
        """Filter data based on the selected view"""
        if df is None:
            return None, None
            
        view = st.session_state.view
        selected_date = st.session_state.selected_date
        
        if view == "monthly":
            year = selected_date.year
            month = selected_date.month
            filtered_data = df[(df['year'] == year) & (df['month'] == month)]
            filtered_forecast = forecast_df[(forecast_df['year'] == year) & (forecast_df['month'] == month)] if forecast_df is not None else None
            
        elif view == "weekly":
            end_date = selected_date + datetime.timedelta(days=6)
            filtered_data = df[(df['date'] >= selected_date) & (df['date'] <= end_date)]
            filtered_forecast = forecast_df[(forecast_df['date'] >= selected_date) & (forecast_df['date'] <= end_date)] if forecast_df is not None else None
            
        elif view == "daily":
            filtered_data = df[df['date'] == selected_date]
            filtered_forecast = forecast_df[forecast_df['date'] == selected_date] if forecast_df is not None else None
            
        elif view == "hourly":
            hour = st.session_state.get('selected_hour', 0)
            filtered_data = df[(df['date'] == selected_date) & (df['hour'] == hour)]
            filtered_forecast = forecast_df[(forecast_df['date'] == selected_date) & (forecast_df['hour'] == hour)] if forecast_df is not None else None
        
        return filtered_data, filtered_forecast
    
    def display_key_metrics(self, filtered_data, filtered_forecast):
        """Display key metrics at the top of the dashboard"""
        st.markdown("<h2 class='sub-header'>Key Metrics</h2>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if filtered_data is not None and not filtered_data.empty:
                max_demand = filtered_data['demand_mw'].max()
                st.metric("Peak Demand", f"{max_demand:.1f} MW")
            else:
                st.metric("Peak Demand", "N/A")
        
        with col2:
            if filtered_data is not None and not filtered_data.empty:
                avg_demand = filtered_data['demand_mw'].mean()
                st.metric("Average Demand", f"{avg_demand:.1f} MW")
            else:
                st.metric("Average Demand", "N/A")
        
        with col3:
            if filtered_data is not None and not filtered_data.empty:
                min_demand = filtered_data['demand_mw'].min()
                st.metric("Minimum Demand", f"{min_demand:.1f} MW")
            else:
                st.metric("Minimum Demand", "N/A")
        
        with col4:
            if filtered_forecast is not None and not filtered_forecast.empty:
                forecast_peak = filtered_forecast['demand_mw'].max()
                if filtered_data is not None and not filtered_data.empty:
                    current_peak = filtered_data['demand_mw'].max()
                    delta = (forecast_peak - current_peak) / current_peak * 100
                    st.metric("Forecast Peak", f"{forecast_peak:.1f} MW", delta=f"{delta:.1f}%")
                else:
                    st.metric("Forecast Peak", f"{forecast_peak:.1f} MW")
            else:
                st.metric("Forecast Peak", "N/A")
    
    def display_power_demand_chart(self, filtered_data, filtered_forecast):
        """Display the main power demand chart"""
        st.markdown("<h2 class='sub-header'>Power Demand Visualization</h2>", unsafe_allow_html=True)
        
        if filtered_data is None or filtered_data.empty:
            st.warning("No data available for the selected time period.")
            return
        
        # Create figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add historical data trace
        if st.session_state.get('show_historical', True):
            fig.add_trace(
                go.Scatter(
                    x=filtered_data['timestamp'],
                    y=filtered_data['demand_mw'],
                    name="Historical Demand",
                    line=dict(color="#1E88E5", width=2)
                )
            )
        
        # Add forecast data if available
        if filtered_forecast is not None and not filtered_forecast.empty and st.session_state.get('show_forecast', True):
            fig.add_trace(
                go.Scatter(
                    x=filtered_forecast['timestamp'],
                    y=filtered_forecast['demand_mw'],
                    name="Forecast Demand",
                    line=dict(color="#FFA000", width=2, dash='dash')
                )
            )
        
        # Customize layout
        title = f"Power Demand - {st.session_state.view.capitalize()} View"
        if st.session_state.view == "monthly":
            title += f" ({st.session_state.selected_date.strftime('%B %Y')})"
        elif st.session_state.view == "weekly":
            end_date = st.session_state.selected_date + datetime.timedelta(days=6)
            title += f" ({st.session_state.selected_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')})"
        elif st.session_state.view == "daily":
            title += f" ({st.session_state.selected_date.strftime('%d %B %Y')})"
        elif st.session_state.view == "hourly":
            title += f" ({st.session_state.selected_date.strftime('%d %B %Y')} {st.session_state.selected_hour}:00)"
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Power Demand (MW)",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_insights(self, filtered_data, filtered_forecast):
        """Display insights based on the data"""
        st.markdown("<h2 class='sub-header'>Insights & Analysis</h2>", unsafe_allow_html=True)
        
        if filtered_data is None or filtered_data.empty:
            st.warning("No data available for insights.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='insight-box'>", unsafe_allow_html=True)
            st.subheader("Consumption Patterns")
            
            # Time-based patterns
            if st.session_state.view in ["monthly", "weekly"]:
                # Group by hour to show daily pattern
                hourly_avg = filtered_data.groupby('hour')['demand_mw'].mean().reset_index()
                
                fig = px.line(
                    hourly_avg, 
                    x='hour', 
                    y='demand_mw',
                    labels={'hour': 'Hour of Day', 'demand_mw': 'Average Demand (MW)'},
                    title="Daily Consumption Pattern"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                peak_hour = hourly_avg.loc[hourly_avg['demand_mw'].idxmax(), 'hour']
                st.markdown(f"⚡ **Peak demand typically occurs around {peak_hour}:00**")
                
            elif st.session_state.view == "daily":
                # Show hourly breakdown for the day
                fig = px.bar(
                    filtered_data,
                    x='hour',
                    y='demand_mw',
                    color='demand_mw',
                    color_continuous_scale='Blues',
                    labels={'hour': 'Hour of Day', 'demand_mw': 'Demand (MW)'},
                    title="Hourly Consumption"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='insight-box'>", unsafe_allow_html=True)
            st.subheader("Comparative Analysis")
            
            if st.session_state.view == "monthly":
                # Compare with previous month
                current_month = st.session_state.selected_date.month
                current_year = st.session_state.selected_date.year
                
                # Calculate previous month
                if current_month == 1:
                    prev_month = 12
                    prev_year = current_year - 1
                else:
                    prev_month = current_month - 1
                    prev_year = current_year
                
                # Get data for previous month
                prev_month_data = self.data[(self.data['year'] == prev_year) & (self.data['month'] == prev_month)]
                
                if not prev_month_data.empty:
                    current_avg = filtered_data['demand_mw'].mean()
                    prev_avg = prev_month_data['demand_mw'].mean()
                    change_pct = (current_avg - prev_avg) / prev_avg * 100
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=['Previous Month', 'Current Month'],
                        y=[prev_avg, current_avg],
                        marker_color=['#90CAF9', '#1E88E5']
                    ))
                    fig.update_layout(
                        title="Month-over-Month Comparison",
                        yaxis_title="Average Demand (MW)",
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    if change_pct > 0:
                        st.markdown(f"📈 **Demand increased by {change_pct:.1f}% compared to previous month**")
                    else:
                        st.markdown(f"📉 **Demand decreased by {abs(change_pct):.1f}% compared to previous month**")
            
            elif st.session_state.view == "daily":
                # Compare with same day last week
                current_date = st.session_state.selected_date
                last_week_date = current_date - datetime.timedelta(days=7)
                
                last_week_data = self.data[self.data['date'] == last_week_date]
                
                if not last_week_data.empty:
                    # Group by hour for comparison
                    current_hourly = filtered_data.groupby('hour')['demand_mw'].mean().reset_index()
                    last_week_hourly = last_week_data.groupby('hour')['demand_mw'].mean().reset_index()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=current_hourly['hour'],
                        y=current_hourly['demand_mw'],
                        name="Current Day",
                        line=dict(color="#1E88E5", width=2)
                    ))
                    fig.add_trace(go.Scatter(
                        x=last_week_hourly['hour'],
                        y=last_week_hourly['demand_mw'],
                        name="Same Day Last Week",
                        line=dict(color="#90CAF9", width=2, dash='dot')
                    ))
                    fig.update_layout(
                        title="Day-over-Day Comparison",
                        xaxis_title="Hour of Day",
                        yaxis_title="Demand (MW)",
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def display_forecast_insights(self, filtered_forecast):
        """Display forecast insights"""
        if filtered_forecast is None or filtered_forecast.empty or not st.session_state.get('show_forecast', True):
            return
            
        st.markdown("<h2 class='sub-header'>Forecast Insights</h2>", unsafe_allow_html=True)
        st.markdown("<div class='insight-box'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Forecast summary stats
            forecast_peak = filtered_forecast['demand_mw'].max()
            forecast_avg = filtered_forecast['demand_mw'].mean()
            forecast_min = filtered_forecast['demand_mw'].min()
            
            st.subheader("Forecast Summary")
            st.markdown(f"""
            - **Peak Demand Forecast:** {forecast_peak:.1f} MW
            - **Average Demand Forecast:** {forecast_avg:.1f} MW
            - **Minimum Demand Forecast:** {forecast_min:.1f} MW
            """)
            
            peak_timestamp = filtered_forecast.loc[filtered_forecast['demand_mw'].idxmax(), 'timestamp']
            peak_date = peak_timestamp.strftime('%d %B %Y')
            peak_time = peak_timestamp.strftime('%H:%M')
            
            st.markdown(f"⚠️ **Expected peak on {peak_date} at {peak_time}**")
        
        with col2:
            # Distribution of forecast
            fig = px.histogram(
                filtered_forecast,
                x='demand_mw',
                nbins=20,
                color_discrete_sequence=['#FFA000'],
                labels={'demand_mw': 'Demand (MW)'},
                title="Forecast Demand Distribution"
            )
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    def display_footer(self):
        """Display application footer"""
        st.markdown("---")
        st.markdown(
            "<p style='text-align:center'>Delhi Power Consumption Forecast Application | &copy; 2024</p>",
            unsafe_allow_html=True
        )
    
    def run(self):
        """Main application execution"""
        # Check authentication
        if not st.session_state.authenticated:
            self.display_header()
            if not self.authenticate_user():
                return
            # Reload the app after authentication
            st.rerun()
        
        # Display header
        self.display_header()
        
        # Data should already be loaded during authentication, but check just in case
        if not st.session_state.data_loaded or self.data is None:
            # Data not loaded yet (should be rare)
            self.load_sample_data()
            self.generate_sample_forecast()
            st.session_state.data_loaded = True
        
        # Display sidebar
        self.display_sidebar()
        
        # Filter data based on view
        filtered_data, filtered_forecast = self.filter_data_by_view(self.data, self.forecasts)
        
        # Display key metrics
        self.display_key_metrics(filtered_data, filtered_forecast)
        
        # Display main chart
        self.display_power_demand_chart(filtered_data, filtered_forecast)
        
        # Display insights
        self.display_insights(filtered_data, filtered_forecast)
        
        # Display forecast insights
        self.display_forecast_insights(filtered_forecast)
        
        # Display footer
        self.display_footer()
        
        # Log page view
        logger.info(f"Page viewed: {st.session_state.view} view by {st.session_state.user_info.get('name', 'Unknown')}")


if __name__ == "__main__":
    # Create and run the application
    app = PowerForecastApp()
    app.run()