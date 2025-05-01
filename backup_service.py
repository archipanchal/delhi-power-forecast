#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backup Service for Delhi Power Consumption Forecast Application.
Provides automated backup, integrity verification, and restoration capabilities.
"""

import os
import sys
import shutil
import json
import hashlib
import time
import logging
import zipfile
import schedule
import threading
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('backup_service')

class BackupService:
    """
    Comprehensive backup service for application data and configurations.
    Supports creating backups, verifying integrity, and restoring from backups.
    """

    def __init__(self, config_path: str = 'config/backup_config.json'):
        """
        Initialize the backup service with configuration.
        
        Args:
            config_path (str): Path to the backup configuration file
        """
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = Path('backups')
        self.backup_dir.mkdir(exist_ok=True)
        
        # Default configuration
        self.config = {
            'data_paths': [
                'data/raw',
                'data/processed',
                'data/models'
            ],
            'config_paths': [
                'config'
            ],
            'retention_days': 30,
            'compression_level': 9,
            'backup_schedule': '0 3 * * *',  # 3 AM daily
            'verify_integrity': True
        }
        
        # Load configuration if exists
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
                logger.info(f"Loaded backup configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading backup configuration: {str(e)}")
    
    def create_backup(self) -> str:
        """
        Create a full backup of application data and configuration.
        
        Returns:
            str: Path to the created backup file
        """
        logger.info("Starting backup creation process")
        backup_filename = f"backup_{self.timestamp}.zip"
        backup_path = self.backup_dir / backup_filename
        manifest = []
        
        try:
            with zipfile.ZipFile(backup_path, 'w', 
                                compression=zipfile.ZIP_DEFLATED, 
                                compresslevel=self.config['compression_level']) as zipf:
                
                # Backup data directories
                for data_path in self.config['data_paths']:
                    path = Path(data_path)
                    if path.exists():
                        logger.info(f"Backing up data directory: {data_path}")
                        for file_path in path.glob('**/*'):
                            if file_path.is_file():
                                relative_path = file_path.relative_to(Path.cwd())
                                zipf.write(file_path, relative_path)
                                file_hash = self._calculate_file_hash(file_path)
                                manifest.append({
                                    'path': str(relative_path),
                                    'size': file_path.stat().st_size,
                                    'modified': datetime.datetime.fromtimestamp(
                                        file_path.stat().st_mtime).isoformat(),
                                    'sha256': file_hash
                                })
                
                # Backup configuration files
                for config_path in self.config['config_paths']:
                    path = Path(config_path)
                    if path.exists():
                        logger.info(f"Backing up configuration directory: {config_path}")
                        for file_path in path.glob('**/*'):
                            if file_path.is_file():
                                relative_path = file_path.relative_to(Path.cwd())
                                zipf.write(file_path, relative_path)
                                file_hash = self._calculate_file_hash(file_path)
                                manifest.append({
                                    'path': str(relative_path),
                                    'size': file_path.stat().st_size,
                                    'modified': datetime.datetime.fromtimestamp(
                                        file_path.stat().st_mtime).isoformat(),
                                    'sha256': file_hash
                                })
                
                # Add manifest to the backup
                manifest_data = json.dumps({
                    'timestamp': self.timestamp,
                    'files': manifest,
                    'total_files': len(manifest)
                }, indent=2)
                zipf.writestr('manifest.json', manifest_data)
            
            backup_size = os.path.getsize(backup_path)
            logger.info(f"Backup completed: {backup_path} ({self._format_size(backup_size)})")
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def restore_backup(self, backup_id: Optional[str] = None) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_id (str, optional): Timestamp or filename of the backup to restore.
                                      If None, the most recent backup will be used.
        
        Returns:
            bool: True if restoration was successful, False otherwise
        """
        backup_path = self._find_backup(backup_id)
        if not backup_path:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        logger.info(f"Starting restoration from backup: {backup_path}")
        
        # Create a temporary directory for extraction
        temp_dir = Path('temp_restore')
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        try:
            # Extract the backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Verify integrity if configured
            if self.config['verify_integrity']:
                logger.info("Verifying backup integrity")
                if not self._verify_integrity(backup_path, temp_dir):
                    logger.error("Backup integrity verification failed, aborting restore")
                    return False
            
            # Restore files
            manifest_path = temp_dir / 'manifest.json'
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            for file_info in manifest['files']:
                source_path = temp_dir / file_info['path']
                target_path = Path(file_info['path'])
                
                # Create parent directories if they don't exist
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                if source_path.exists():
                    shutil.copy2(source_path, target_path)
            
            logger.info(f"Successfully restored {len(manifest['files'])} files from backup")
            return True
            
        except Exception as e:
            logger.error(f"Restoration failed: {str(e)}")
            return False
            
        finally:
            # Clean up temporary files
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def list_backups(self) -> List[Dict]:
        """
        List all available backups with metadata.
        
        Returns:
            List[Dict]: List of backup information dictionaries
        """
        backups = []
        for backup_file in sorted(self.backup_dir.glob('backup_*.zip'), reverse=True):
            try:
                with zipfile.ZipFile(backup_file, 'r') as zipf:
                    if 'manifest.json' in zipf.namelist():
                        manifest_data = json.loads(zipf.read('manifest.json'))
                        backups.append({
                            'filename': backup_file.name,
                            'path': str(backup_file),
                            'timestamp': manifest_data['timestamp'],
                            'size': self._format_size(backup_file.stat().st_size),
                            'total_files': manifest_data['total_files']
                        })
                    else:
                        # Handle backups without manifest
                        backups.append({
                            'filename': backup_file.name,
                            'path': str(backup_file),
                            'timestamp': backup_file.name.replace('backup_', '').replace('.zip', ''),
                            'size': self._format_size(backup_file.stat().st_size),
                            'total_files': 'Unknown'
                        })
            except Exception as e:
                logger.warning(f"Error reading backup {backup_file}: {str(e)}")
        
        return backups
    
    def _find_backup(self, backup_id: Optional[str] = None) -> Optional[Path]:
        """
        Find a backup by ID (timestamp or filename).
        
        Args:
            backup_id (str, optional): Timestamp or filename of the backup.
                                      If None, returns the most recent backup.
        
        Returns:
            Optional[Path]: Path to the backup file, or None if not found
        """
        if not backup_id:
            # Get the most recent backup
            backups = sorted(self.backup_dir.glob('backup_*.zip'), key=os.path.getmtime, reverse=True)
            return backups[0] if backups else None
        
        # Check if the ID is a full filename
        if backup_id.endswith('.zip'):
            backup_path = self.backup_dir / backup_id
            return backup_path if backup_path.exists() else None
        
        # Check if the ID is a timestamp
        backup_path = self.backup_dir / f"backup_{backup_id}.zip"
        if backup_path.exists():
            return backup_path
        
        # Search for backup containing the ID
        for backup_file in self.backup_dir.glob('backup_*.zip'):
            if backup_id in backup_file.name:
                return backup_file
        
        return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path (Path): Path to the file
        
        Returns:
            str: Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _verify_integrity(self, backup_path: Path, extract_dir: Path) -> bool:
        """
        Verify the integrity of an extracted backup.
        
        Args:
            backup_path (Path): Path to the backup file
            extract_dir (Path): Directory where the backup was extracted
        
        Returns:
            bool: True if integrity check passed, False otherwise
        """
        try:
            # Read the manifest
            manifest_path = extract_dir / 'manifest.json'
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            for file_info in manifest['files']:
                file_path = extract_dir / file_info['path']
                if not file_path.exists():
                    logger.error(f"File missing from backup: {file_info['path']}")
                    return False
                
                # Verify file hash
                actual_hash = self._calculate_file_hash(file_path)
                if actual_hash != file_info['sha256']:
                    logger.error(f"File integrity check failed for {file_info['path']}")
                    logger.error(f"Expected: {file_info['sha256']}, Got: {actual_hash}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Integrity verification failed: {str(e)}")
            return False
    
    def _cleanup_old_backups(self) -> None:
        """
        Remove backups older than the retention period.
        """
        retention_days = self.config.get('retention_days', 30)
        if retention_days <= 0:
            return
        
        cutoff_time = time.time() - (retention_days * 86400)
        for backup_file in self.backup_dir.glob('backup_*.zip'):
            if backup_file.stat().st_mtime < cutoff_time:
                logger.info(f"Removing old backup: {backup_file}")
                backup_file.unlink()
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes (int): Size in bytes
        
        Returns:
            str: Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def schedule_backups() -> None:
    """
    Schedule automatic backups based on configuration.
    This function starts a background thread that runs indefinitely.
    """
    backup_service = BackupService()
    schedule_str = backup_service.config.get('backup_schedule', '0 3 * * *')
    
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    logger.info(f"Scheduling automatic backups with schedule: {schedule_str}")
    
    # Parse cron-style schedule and convert to schedule library calls
    schedule_parts = schedule_str.split()
    if len(schedule_parts) == 5:
        minute, hour, day, month, weekday = schedule_parts
        
        if minute == '*':
            job = schedule.every().hour
        else:
            job = schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}")
        
        job.do(backup_service.create_backup)
        logger.info("Automatic backup scheduling configured successfully")
        
        # Start the schedule in a background thread
        thread = threading.Thread(target=run_schedule, daemon=True)
        thread.start()
        return thread
    else:
        logger.error(f"Invalid backup schedule format: {schedule_str}")
        return None


if __name__ == "__main__":
    # Create backup service
    service = BackupService()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            service.create_backup()
        
        elif command == "list":
            backups = service.list_backups()
            print(f"Available backups ({len(backups)}):")
            for i, backup in enumerate(backups):
                print(f"{i+1}. {backup['filename']} - {backup['timestamp']} - {backup['size']} - {backup['total_files']} files")
        
        elif command == "restore" and len(sys.argv) > 2:
            backup_id = sys.argv[2]
            service.restore_backup(backup_id)
        
        elif command == "schedule":
            thread = schedule_backups()
            print("Backup scheduling started in background. Press Ctrl+C to exit.")
            try:
                while thread and thread.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Backup scheduling stopped.")
        
        else:
            print("Usage:")
            print("  python backup_service.py create              # Create a new backup")
            print("  python backup_service.py list                # List available backups")
            print("  python backup_service.py restore [backup_id] # Restore from a backup")
            print("  python backup_service.py schedule            # Start automatic backup scheduling")
    
    else:
        # Create a backup by default
        service.create_backup() 