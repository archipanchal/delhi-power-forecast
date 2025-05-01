# This file is intentionally left empty to make the directory a Python package

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel Deployment Script for Delhi Power Consumption Forecast Application.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vercel_deploy")

def check_vercel_cli():
    """Check if Vercel CLI is installed"""
    try:
        logger.info("Checking for Vercel CLI...")
        result = subprocess.run(['vercel', '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        if result.returncode != 0:
            logger.error("Vercel CLI not found. Please install it using: npm i -g vercel")
            return False
        logger.info(f"Vercel CLI found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        logger.error("Vercel CLI not found. Please install it using: npm i -g vercel")
        return False

def deploy_to_vercel(production=True):
    """Deploy to Vercel"""
    start_time = datetime.now()
    
    if not check_vercel_cli():
        return False
    
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
        
        # Print the output regardless of success/failure
        print(result.stdout)
        
        if result.returncode != 0:
            logger.error(f"Deployment failed: {result.stderr}")
            return False
        
        # Try to extract the deployment URL
        import re
        url_match = re.search(r'(https://[^\s]+\.vercel\.app)', result.stdout)
        if url_match:
            deployment_url = url_match.group(1)
            logger.info(f"Deployment successful! Your application is live at: {deployment_url}")
        else:
            logger.info("Deployment successful!")
        
        logger.info(f"Deployment completed in {datetime.now() - start_time}")
        return True
        
    except Exception as e:
        logger.error(f"Error during deployment: {str(e)}")
        return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy to Vercel')
    parser.add_argument('--preview', action='store_true', help='Deploy to preview (default is production)')
    
    args = parser.parse_args()
    
    # By default, deploy to production unless preview flag is specified
    production = not args.preview
    
    # Deploy to Vercel
    success = deploy_to_vercel(production=production)
    
    if success:
        logger.info("Vercel deployment completed successfully")
        return 0
    else:
        logger.error("Vercel deployment failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
