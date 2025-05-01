# Delhi Power Consumption Forecast Application

A web application for visualizing and forecasting electricity demand in Delhi. This application uses machine learning to predict power consumption patterns based on historical data and weather conditions.

## Features & Technical Implementation

### Security & Authentication
- **Multi-Factor Login**: Email verification and mobile verification for secure access
- **SSO Integration**: Single Sign-On support with Google and Microsoft authentication
- **Input Validation**: Robust validation for all user inputs including email and mobile formats
- **HTTPS Support**: Self-signed certificates for secure connections

### Data Analytics & Visualization
- **Interactive Dashboard**: Visualize historical power consumption patterns
- **ML-Powered Forecasting**: Predict future power demand using LSTM models
- **Comparative Analysis**: Compare current consumption with historical patterns

### System Infrastructure
- **Comprehensive Logging**: Detailed activity tracking for system monitoring
- **Backup & Recovery**: Automated backup system with data integrity checks
- **Docker Containerization**: Containerized deployment for consistent environments
- **CI/CD Pipeline**: Automated testing and deployment with GitHub Actions

## Technical Components

### 1. Technical Implementation (Weightage: 35)
- **Logging System**: Complete logging of system interactions using a custom logging module (`logging_system.py`)
- **HTTPS Implementation**: Self-signed certificate generation and HTTPS server (`https_server.py`)
- **Backup & Recovery**: Comprehensive backup system with integrity verification (`backup_service.py`)
- **Live Hosting**: Support for Vercel, Docker, and Kubernetes deployment
- **Login Module**: Email and mobile verification with validation
- **SSO Integration**: Support for Google and Microsoft OAuth (`sso_auth.py`)
- **Input Validation**: Robust validation for all user inputs

### 2. Use of DevOps Tools (Weightage: 25)
- **Code Repository**: GitHub with more than 10 functionalities
- **Build System**: Docker and docker-compose for containerization
- **Testing**: Automated testing with pytest (`test_power_forecast.py`)
- **Release Management**: CI/CD pipeline with GitHub Actions
- **Deployment**: Support for multiple deployment options including Docker, Kubernetes, and Vercel

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/archipanchal/delhi-power-forecast.git
   cd delhi-power-forecast
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Create a `.env` file in the project root with the following variables:
   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   ```

## Running the Application

### Development Mode

To run the application in development mode:

```
streamlit run power_forecast_app.py
```

### HTTPS Mode

To run the application with HTTPS:

```
python https_server.py
```

This will generate a self-signed certificate and start the application with HTTPS.

### Docker Deployment

To run the application using Docker:

```
docker-compose up -d
```

## Backup System

The application includes a comprehensive backup system for data protection.

### Creating a Backup

```
python -c "from backup_service import BackupService; BackupService().create_backup()"
```

### Restoring from Backup

```
python -c "from backup_service import BackupService; BackupService().restore_backup('TIMESTAMP')"
```

Where `TIMESTAMP` is the timestamp of the backup to restore.

## Running Tests

To run the automated tests:

```
pytest
```

## CI/CD Pipeline

The application uses GitHub Actions for continuous integration and deployment:
- Automated testing on each push and pull request
- Docker image building and publishing
- Deployment to production environments

## License

[MIT License](LICENSE)

## Contact

For support or inquiries, please contact [developer-email@example.com](mailto:developer-email@example.com). 