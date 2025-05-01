#!/usr/bin/env python3
"""
Deployment script for Delhi Power Consumption Forecast Application.
This script handles deployment to various environments and server configurations.
"""

import os
import sys
import subprocess
import argparse
import logging
import json
import shutil
import time
import socket
import platform
import getpass
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Constants
APP_NAME = "Delhi Power Forecast"
APP_VERSION = "1.0.0"
DEFAULT_PORT = 8501
DEFAULT_ENV = "development"

class Deployment:
    """Handles deployment of the application to various environments"""
    
    def __init__(self, env="development", port=DEFAULT_PORT, use_https=True):
        self.env = env
        self.port = port
        self.use_https = use_https
        self.deployment_dir = f"deployment_{env}"
        self.config_dir = os.path.join(self.deployment_dir, ".streamlit")
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.start_time = datetime.now()
        
        # Deployment configuration
        self.config = {
            "development": {
                "host": "localhost",
                "port": 8501,
                "ssl_verify": False
            },
            "staging": {
                "host": "0.0.0.0",  # Listen on all interfaces
                "port": 8502,
                "ssl_verify": True
            },
            "production": {
                "host": "0.0.0.0",  # Listen on all interfaces
                "port": 80,
                "ssl_verify": True
            }
        }
    
    def deploy(self):
        """Deploy the application"""
        logger.info(f"Deploying {APP_NAME} v{APP_VERSION} to {self.env} environment")
        
        # Create deployment directory
        self._setup_deployment_dir()
        
        # Copy application files
        self._copy_app_files()
        
        # Set up configuration
        self._configure_app()
        
        # Start the application
        if self._start_app():
            logger.info(f"Deployment completed successfully in {datetime.now() - self.start_time}")
            self._show_deployment_info()
            return True
        else:
            logger.error("Deployment failed")
            return False
    
    def _setup_deployment_dir(self):
        """Set up the deployment directory"""
        logger.info(f"Setting up deployment directory: {self.deployment_dir}")
        
        if os.path.exists(self.deployment_dir):
            logger.info(f"Removing existing deployment directory: {self.deployment_dir}")
            shutil.rmtree(self.deployment_dir)
        
        os.makedirs(self.deployment_dir)
        os.makedirs(self.config_dir, exist_ok=True)
        logger.info(f"Created deployment directory: {self.deployment_dir}")
    
    def _copy_app_files(self):
        """Copy application files to deployment directory"""
        logger.info("Copying application files to deployment directory")
        
        # Files to copy
        files_to_copy = [
            # Main application file
            "power_forecast_app.py",
            # Data files
            "powerdemand_5min_2021_to_2024_with weather.csv",
            "power_demand_lstm.h5",
            "power_demand_scaler.pkl",
            # Configuration
            "requirements.txt",
            ".env",
            # Support files
            "logging_system.py",
            "backup_service.py",
        ]
        
        # Copy each file
        for file in files_to_copy:
            if os.path.exists(file):
                try:
                    if os.path.isdir(file):
                        shutil.copytree(file, os.path.join(self.deployment_dir, file))
                    else:
                        shutil.copy2(file, os.path.join(self.deployment_dir, file))
                    logger.info(f"Copied {file}")
                except Exception as e:
                    logger.warning(f"Failed to copy {file}: {str(e)}")
            else:
                logger.warning(f"File not found: {file}")
        
        # Create deployment info file
        deployment_info = {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "environment": self.env,
            "deployed_at": datetime.now().isoformat(),
            "deployed_by": getpass.getuser(),
            "host": platform.node(),
            "os": platform.platform(),
            "python_version": platform.python_version()
        }
        
        with open(os.path.join(self.deployment_dir, "deployment_info.json"), "w") as f:
            json.dump(deployment_info, f, indent=4)
    
    def _configure_app(self):
        """Configure the application for the target environment"""
        logger.info(f"Configuring application for {self.env} environment")
        
        # Create Streamlit config
        config = {
            "server": {
                "enableCORS": False,
                "enableXsrfProtection": True,
                "port": self.config[self.env]["port"],
                "address": self.config[self.env]["host"]
            },
            "browser": {
                "serverAddress": self.config[self.env]["host"] if self.config[self.env]["host"] != "0.0.0.0" else "localhost",
                "serverPort": self.config[self.env]["port"]
            },
            "runner": {
                "fastReruns": False
            }
        }
        
        # Add SSL configuration if using HTTPS
        if self.use_https:
            cert_dir = os.path.join(self.deployment_dir, "certs")
            os.makedirs(cert_dir, exist_ok=True)
            
            cert_file = os.path.join(cert_dir, "server.crt")
            key_file = os.path.join(cert_dir, "server.key")
            
            # Copy existing certificates if available, otherwise generate new ones
            if os.path.exists("certs/server.crt") and os.path.exists("certs/server.key"):
                shutil.copy2("certs/server.crt", cert_file)
                shutil.copy2("certs/server.key", key_file)
                logger.info("Using existing SSL certificates")
            else:
                logger.info("Generating new SSL certificates")
                try:
                    from https_server import generate_self_signed_cert
                    if not generate_self_signed_cert(cert_file, key_file):
                        logger.error("Failed to generate SSL certificates")
                        raise Exception("Certificate generation failed")
                except ImportError:
                    logger.error("Could not import certificate generation module")
                    raise Exception("Could not generate certificates, https_server.py not found")
            
            config["server"]["sslCertFile"] = cert_file
            config["server"]["sslKeyFile"] = key_file
        
        # Write Streamlit config
        config_file = os.path.join(self.config_dir, "config.toml")
        with open(config_file, "w") as f:
            for section, options in config.items():
                f.write(f"[{section}]\n")
                for key, value in options.items():
                    if isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    else:
                        f.write(f"{key} = {value}\n")
                f.write("\n")
        
        logger.info(f"Created Streamlit configuration: {config_file}")
        
        # Create .env file for environment-specific settings
        env_file = os.path.join(self.deployment_dir, ".env")
        with open(env_file, "w") as f:
            f.write(f"ENVIRONMENT={self.env}\n")
            f.write(f"LOG_LEVEL=INFO\n")
            
            # Copy variables from existing .env file
            if os.path.exists(".env"):
                with open(".env", "r") as source_env:
                    for line in source_env:
                        if not line.strip().startswith("#") and "=" in line:
                            key = line.split("=")[0].strip()
                            if key not in ["ENVIRONMENT", "LOG_LEVEL"]:
                                f.write(line)
        
        logger.info(f"Created environment file: {env_file}")
    
    def _start_app(self):
        """Start the Streamlit application"""
        logger.info("Starting application")
        
        # Change to deployment directory
        os.chdir(self.deployment_dir)
        
        # Start command
        cmd = [
            sys.executable, "-m", "streamlit", "run", "power_forecast_app.py",
            "--server.port", str(self.config[self.env]["port"]),
            "--server.address", self.config[self.env]["host"]
        ]
        
        # Start in the background for production deployments
        if self.env in ["staging", "production"]:
            logger.info("Starting application in background mode")
            try:
                if platform.system() == "Windows":
                    # Use pythonw for background processes on Windows
                    cmd[0] = cmd[0].replace("python", "pythonw")
                    process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    # Use nohup for Unix-like systems
                    cmd = ["nohup"] + cmd + ["&"]
                    process = subprocess.Popen(" ".join(cmd), shell=True)
                
                # Wait a moment to make sure the process starts
                time.sleep(2)
                
                # Check if the port is in use
                if self._is_port_in_use(self.config[self.env]["port"]):
                    logger.info(f"Application is running on port {self.config[self.env]['port']}")
                    
                    # Save PID to file
                    with open("app.pid", "w") as f:
                        f.write(str(process.pid))
                    
                    return True
                else:
                    logger.error(f"Application failed to start on port {self.config[self.env]['port']}")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to start application: {str(e)}")
                return False
        else:
            # For development, start in foreground
            logger.info("Starting application in foreground mode")
            try:
                process = subprocess.Popen(cmd)
                logger.info(f"Application started with PID: {process.pid}")
                return True
            except Exception as e:
                logger.error(f"Failed to start application: {str(e)}")
                return False
    
    def _is_port_in_use(self, port):
        """Check if a port is in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def _show_deployment_info(self):
        """Show deployment information"""
        host = self.config[self.env]["host"]
        if host == "0.0.0.0":
            host = "localhost"
        
        protocol = "https" if self.use_https else "http"
        port = self.config[self.env]["port"]
        port_str = f":{port}" if port != 80 else ""
        
        url = f"{protocol}://{host}{port_str}"
        
        print("\n" + "=" * 60)
        print(f"  {APP_NAME} v{APP_VERSION} deployed to {self.env} environment")
        print("=" * 60)
        print(f"  URL: {url}")
        print(f"  Deployment directory: {os.path.abspath(self.deployment_dir)}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.use_https and self.env != "production":
            print("\n  Note: Using self-signed certificate for HTTPS.")
            print("  You may see security warnings in your browser.")
            print("  This is normal in development/staging environments.")
        
        if self.env in ["staging", "production"]:
            print("\n  The application is running in the background.")
            print(f"  PID file: {os.path.abspath('app.pid')}")
            print("\n  To stop the application:")
            if platform.system() == "Windows":
                print(f"  taskkill /F /PID <pid>")
            else:
                print(f"  kill $(cat {os.path.abspath('app.pid')})")
        
        print("=" * 60 + "\n")

def create_systemd_service(deployment_dir):
    """Create a systemd service file for production deployments"""
    service_content = f"""[Unit]
Description=Delhi Power Consumption Forecast Application
After=network.target

[Service]
User={getpass.getuser()}
WorkingDirectory={os.path.abspath(deployment_dir)}
ExecStart={sys.executable} -m streamlit run power_forecast_app.py --server.port 80 --server.address 0.0.0.0
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    
    service_file = os.path.join(deployment_dir, "delhi-power-forecast.service")
    with open(service_file, "w") as f:
        f.write(service_content)
    
    logger.info(f"Created systemd service file: {service_file}")
    logger.info("To install the service:")
    logger.info(f"  sudo cp {service_file} /etc/systemd/system/")
    logger.info("  sudo systemctl daemon-reload")
    logger.info("  sudo systemctl enable delhi-power-forecast")
    logger.info("  sudo systemctl start delhi-power-forecast")
    
    return service_file

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description=f"Deploy {APP_NAME} to different environments")
    
    parser.add_argument('--env', choices=['development', 'staging', 'production'],
                       default=DEFAULT_ENV, help=f'Target environment (default: {DEFAULT_ENV})')
    parser.add_argument('--port', type=int, help='Port to run the application on')
    parser.add_argument('--no-https', action='store_true', help='Disable HTTPS')
    parser.add_argument('--systemd', action='store_true', help='Create systemd service file (Linux only)')
    
    args = parser.parse_args()
    
    # Set port based on environment if not specified
    port = args.port
    if port is None:
        port = {
            "development": 8501,
            "staging": 8502,
            "production": 80
        }.get(args.env, DEFAULT_PORT)
    
    # Create deployment
    deployment = Deployment(env=args.env, port=port, use_https=not args.no_https)
    
    # Deploy the application
    if deployment.deploy():
        # Create systemd service file if requested and on Linux
        if args.systemd and args.env == "production" and platform.system() != "Windows":
            create_systemd_service(deployment.deployment_dir)
        
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 