#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vercel Deployment Script for Delhi Power Consumption Forecast Application.
"""

import os
import sys
import subprocess
import json
import time
import argparse
from pathlib import Path

# Try to import our custom logging module
try:
    from logging_system import get_logger
    logger = get_logger('vercel_deploy')
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('vercel_deploy')

class VercelDeployment:
    """Handles deployment to Vercel"""
    
    def __init__(self):
        """Initialize the deployment handler"""
        self.project_root = Path.cwd()
        self.api_dir = self.project_root / 'api'
        self.api_dir.mkdir(exist_ok=True)
        
        # Check if Vercel CLI is installed
        self.check_vercel_cli()

    def check_vercel_cli(self):
        """Check if Vercel CLI is installed"""
        try:
            result = subprocess.run(['vercel', '--version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
            if result.returncode != 0:
                logger.error("Vercel CLI not found. Please install it using: npm i -g vercel")
                sys.exit(1)
            logger.info(f"Vercel CLI found: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Vercel CLI not found. Please install it using: npm i -g vercel")
            sys.exit(1)

    def prepare_deployment(self):
        """Prepare files for deployment"""
        logger.info("Preparing files for Vercel deployment...")
        
        # Ensure api directory exists
        self.api_dir.mkdir(exist_ok=True)
        
        # Create vercel.json if it doesn't exist
        vercel_config_path = self.project_root / 'vercel.json'
        if not vercel_config_path.exists():
            logger.info("Creating vercel.json configuration file")
            vercel_config = {
                "version": 2,
                "builds": [
                    {
                        "src": "api/index.py",
                        "use": "@vercel/python"
                    }
                ],
                "routes": [
                    {
                        "src": "/(.*)",
                        "dest": "/api/index.py"
                    }
                ],
                "env": {
                    "PYTHONPATH": ".",
                    "ENVIRONMENT": "production"
                }
            }
            
            with open(vercel_config_path, 'w') as f:
                json.dump(vercel_config, f, indent=2)
        
        # Check for index.py in api directory
        index_path = self.api_dir / 'index.py'
        if not index_path.exists():
            logger.error("api/index.py is missing. Please create it before deployment.")
            sys.exit(1)
        
        # Copy requirements file for Vercel if it exists
        vercel_req_path = self.project_root / 'requirements-vercel.txt'
        if vercel_req_path.exists():
            logger.info("Copying requirements-vercel.txt to requirements.txt for deployment")
            import shutil
            shutil.copy(vercel_req_path, self.project_root / 'requirements.txt')
        
        logger.info("Deployment preparation complete")

    def deploy(self, production: bool = False):
        """
        Deploy the application to Vercel
        
        Args:
            production: If True, deploy to production, otherwise deploy to preview
        """
        self.prepare_deployment()
        
        logger.info(f"Deploying to Vercel {'production' if production else 'preview'} environment...")
        
        # Build the deployment command
        cmd = ['vercel']
        
        if production:
            cmd.append('--prod')
        
        # Add --yes to skip confirmation prompts
        cmd.append('--yes')
        
        # Execute the deployment
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
            
            if result.returncode != 0:
                logger.error(f"Deployment failed: {result.stderr}")
                sys.exit(1)
            
            # Extract deployment URL from output
            output = result.stdout
            
            # Look for URL in the output (varies depending on Vercel CLI version)
            import re
            url_match = re.search(r'(https://[^\s]+\.vercel\.app)', output)
            
            if url_match:
                deployment_url = url_match.group(1)
                logger.info(f"Deployment successful! Your application is live at: {deployment_url}")
            else:
                logger.info("Deployment successful, but couldn't extract the URL from output.")
                logger.info(f"Output: {output}")
            
        except Exception as e:
            logger.error(f"Error during deployment: {str(e)}")
            sys.exit(1)

    def create_streamlit_deployment(self):
        """
        Create a separate Streamlit deployment configuration
        Note: This is for documentation purposes, as Vercel doesn't directly support Streamlit
        """
        logger.info("Creating Streamlit deployment configuration...")
        
        # Create a dedicated directory for Streamlit deployment
        streamlit_dir = self.project_root / 'streamlit_deploy'
        streamlit_dir.mkdir(exist_ok=True)
        
        # Create README with instructions
        readme_path = streamlit_dir / 'README.md'
        with open(readme_path, 'w') as f:
            f.write("""# Streamlit Deployment

Since Vercel does not natively support Streamlit applications, you'll need to use a different service for hosting the Streamlit part of this application. Here are some recommended options:

## Option 1: Streamlit Sharing (Recommended)
[Streamlit Sharing](https://streamlit.io/sharing) is a free service provided by Streamlit for hosting Streamlit applications.

1. Push your code to a GitHub repository
2. Sign up for Streamlit Sharing
3. Connect your repository and deploy

## Option 2: Heroku
Heroku can host Streamlit applications with a custom Procfile:

```
web: streamlit run power_forecast_app.py --server.port=$PORT
```

## Option 3: AWS EC2 or Google Cloud Run
For more control and scalability, consider using cloud providers like AWS or GCP.

## Connecting Both Parts
The Vercel deployment serves the API and landing page, while the Streamlit deployment hosts the interactive application. You should:

1. Update the landing page in `api/index.py` to point to your Streamlit URL once deployed
2. Configure any API endpoints in your Streamlit app to point to your Vercel deployment

This setup achieves a complete solution with the best of both platforms.
""")
            
        logger.info(f"Streamlit deployment documentation created at {readme_path}")

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Deploy Delhi Power Consumption Forecast to Vercel')
    parser.add_argument('--prod', action='store_true', help='Deploy to production environment')
    parser.add_argument('--prepare-only', action='store_true', help='Only prepare files without deploying')
    args = parser.parse_args()
    
    deployment = VercelDeployment()
    
    if args.prepare_only:
        deployment.prepare_deployment()
        deployment.create_streamlit_deployment()
    else:
        deployment.deploy(production=args.prod)
        deployment.create_streamlit_deployment()

if __name__ == "__main__":
    main()
