# Delhi Power Demand Analysis and Forecasting

A Streamlit application for analyzing historical power demand data and forecasting future power consumption in Delhi.

## Features

- Historical data analysis (2021-2024)
- 2025 power demand forecasting
- Monthly, weekly, and daily analysis views
- Interactive visualizations
- Data export capabilities
- Detailed statistical analysis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/delhi-power-forecast.git
cd delhi-power-forecast
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit application:
```bash
streamlit run power_forecast_app.py
```

2. Access the application in your web browser at `http://localhost:8501`

## Project Structure

```
delhi-power-forecast/
├── power_forecast_app.py    # Main Streamlit application
├── requirements.txt         # Project dependencies
├── README.md               # Project documentation
└── .gitignore              # Git ignore file
```

## Data Sources

The application uses:
- Historical power demand data from 2021-2024
- Sample data for demonstration purposes
- Weather data integration for enhanced forecasting

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Delhi Power Distribution Company
- Weather data providers
- Open-source community contributors 