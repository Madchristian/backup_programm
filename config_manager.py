import configparser
import os

class ConfigManager:
    def __init__(self, config_file='backup_config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        if not os.path.exists(self.config_file):
            self.create_default_config()
        self.load_config()

    def create_default_config(self):
        self.config['DEFAULT'] = {
            'nfs_mount_point': '/mnt/backup',
            'retention_days': '7',
            'backup_hour': '2',
            'backup_minute': '0',
            'discord_webhook_url': '',
            'compress_backups': 'no'
        }
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def load_config(self):
        self.config.read(self.config_file)
        self.nfs_mount_point = self.config['DEFAULT']['nfs_mount_point']
        self.retention_days = int(self.config['DEFAULT']['retention_days'])
        self.backup_hour = int(self.config['DEFAULT']['backup_hour'])
        self.backup_minute = int(self.config['DEFAULT']['backup_minute'])
        self.discord_webhook_url = self.config['DEFAULT'].get('discord_webhook_url', '')
        self.compress_backups = self.config['DEFAULT'].get('compress_backups', 'no').lower() == 'yes'

    def save_config(self):
        self.config['DEFAULT']['nfs_mount_point'] = self.nfs_mount_point
        self.config['DEFAULT']['retention_days'] = str(self.retention_days)
        self.config['DEFAULT']['backup_hour'] = str(self.backup_hour)
        self.config['DEFAULT']['backup_minute'] = str(self.backup_minute)
        self.config['DEFAULT']['discord_webhook_url'] = self.discord_webhook_url
        self.config['DEFAULT']['compress_backups'] = 'yes' if self.compress_backups else 'no'
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
