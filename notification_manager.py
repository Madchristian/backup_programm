## notification_manager.py
import requests
import logging
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

class NotificationManager:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_notification(self, message):
        if not self.webhook_url:
            return
        data = {"content": message}
        try:
            response = requests.post(self.webhook_url, json=data)
            if response.status_code != 204:
                logging.error(f"Fehler beim Senden der Benachrichtigung: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Ausnahme beim Senden der Benachrichtigung: {e}")