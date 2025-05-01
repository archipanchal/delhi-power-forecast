import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from power_forecast_app import predict_2025, filter_forecast_data, load_data

@pytest.fixture
def sample_data():
    """Create sample data for testing"""
    dates = pd.date_range(start='2021-01-01', end='2021-12-31', freq='H')
    power_demand = np.random.normal(3500, 500, len(dates))
    return pd.DataFrame({'Power demand': power_demand}, index=dates)

def test_predict_2025(sample_data):
    """Test the prediction function"""
    forecast = predict_2025(sample_data, "Hourly")
    
    # Check if forecast has correct structure
    assert isinstance(forecast, pd.DataFrame)
    assert 'Power demand' in forecast.columns
    
    # Check if forecast has correct length (8760 hours in a year)
    assert len(forecast) == 8760
    
    # Check if values are within reasonable range
    assert forecast['Power demand'].min() > 0
    assert forecast['Power demand'].max() < 10000

def test_filter_forecast_data(sample_data):
    """Test the data filtering function"""
    # Create sample forecast data
    forecast = predict_2025(sample_data, "Hourly")
    
    # Test monthly filtering
    monthly_data = filter_forecast_data(forecast, selected_month=1)
    assert all(date.month == 1 for date in monthly_data.index)
    
    # Test weekly filtering
    weekly_data = filter_forecast_data(forecast, selected_week=1)
    assert len(weekly_data) <= 168  # Max 168 hours in a week
    
    # Test daily filtering
    test_date = datetime(2025, 1, 1)
    daily_data = filter_forecast_data(forecast, selected_date=test_date)
    assert len(daily_data) <= 24  # 24 hours in a day

def test_load_data():
    """Test the data loading function"""
    df = load_data()
    if df is not None:
        assert isinstance(df, pd.DataFrame)
        assert 'Power demand' in df.columns
        assert isinstance(df.index, pd.DatetimeIndex) 