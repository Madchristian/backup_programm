import os
import shutil
import subprocess
import logging
from datetime import datetime, timedelta
import argparse
import configparser
import sys
import time
import threading
import requests
from tqdm import tqdm  # Fortschrittsbalken-Bibliothek
import tarfile
from colorama import init, Fore, Style
import socket
from cli import CLI
from config_manager import ConfigManager
from notification_manager import NotificationManager
from backup_manager import BackupManager

init(autoreset=True)


# Logging konfigurieren
logging.basicConfig(
    filename='backup.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--service':
        # Service-Modus: keine Benutzerinteraktion, nur geplante Backups
        config = ConfigManager()
        notifier = NotificationManager(config.discord_webhook_url)
        backup_manager = BackupManager(
            config.nfs_mount_point,
            config.retention_days,
            notifier,
            config.compress_backups
        )
        backup_manager.backup_homes()
        backup_manager.rotate_backups()
    else:
        # Interaktiver Modus für manuelle Nutzung
        CLI()
