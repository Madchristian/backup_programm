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

from config_manager import ConfigManager
from backup_manager import BackupManager
from notification_manager import NotificationManager
from scheduler import Scheduler

class CLI:
    def __init__(self):
        self.config = ConfigManager()
        self.notifier = NotificationManager(self.config.discord_webhook_url)
        self.backup_manager = BackupManager(
            self.config.nfs_mount_point,
            self.config.retention_days,
            self.notifier,
            self.config.compress_backups
        )
        self.scheduler = Scheduler(
            self.backup_manager,
            datetime.strptime(f"{self.config.backup_hour}:{self.config.backup_minute}", '%H:%M').time()
        )
        self.scheduler.start()
        self.main_menu()

    def main_menu(self):
        while True:
            print(Fore.BLUE + Style.BRIGHT + "\nBackup-Programm Menü:" + Style.RESET_ALL)
            print("1. Backup jetzt starten")
            print("2. Automatische Backups konfigurieren")
            print("3. Restore durchführen")
            print("4. Datei wiederherstellen")
            print("5. Einstellungen")
            print("6. Beenden")
            choice = input("Bitte wählen Sie eine Option: ")

            if choice == '1':
                self.start_backup()
            elif choice == '2':
                self.configure_scheduler()
            elif choice == '3':
                self.restore_backup()
            elif choice == '4':
                self.restore_file()
            elif choice == '5':
                self.settings_menu()
            elif choice == '6':
                self.exit_program()
            else:
                print(Fore.RED + "Ungültige Auswahl. Bitte versuchen Sie es erneut." + Style.RESET_ALL)


    def start_backup(self):
        print(Fore.GREEN + "\nBackup wird gestartet..." + Style.RESET_ALL)
        success = self.backup_manager.backup_homes()
        if success:
            self.backup_manager.rotate_backups()
            print(Fore.GREEN + "Backup abgeschlossen." + Style.RESET_ALL)
        else:
            print(Fore.RED + "Backup fehlgeschlagen. Siehe Logs für Details." + Style.RESET_ALL)


    def configure_scheduler(self):
        print("\nAutomatische Backups konfigurieren:")
        hour = input(f"Backup-Stunde (0-23) [{self.config.backup_hour}]: ") or self.config.backup_hour
        minute = input(f"Backup-Minute (0-59) [{self.config.backup_minute}]: ") or self.config.backup_minute

        self.config.backup_hour = int(hour)
        self.config.backup_minute = int(minute)
        self.config.save_config()

        self.scheduler.stop()
        self.scheduler = Scheduler(
            self.backup_manager,
            datetime.strptime(f"{self.config.backup_hour}:{self.config.backup_minute}", '%H:%M').time()
        )
        self.scheduler.start()
        print("Automatische Backups wurden aktualisiert.")

    def restore_backup(self):
        backups = self.backup_manager.list_backups()
        if not backups:
            print("Keine Backups verfügbar.")
            return

        # Benutzer auswählen
        users = sorted(set([b['user'] for b in backups]))
        print("\nVerfügbare Benutzer:")
        for idx, user in enumerate(users, 1):
            print(f"{idx}. {user}")
        print("0. Abbrechen")

        while True:
            user_choice = input("Bitte wählen Sie einen Benutzer (Nummer, 0 zum Abbrechen): ")
            if user_choice == '0':
                print("Wiederherstellung abgebrochen.")
                return
            try:
                user_idx = int(user_choice) - 1
                if user_idx < 0 or user_idx >= len(users):
                    raise ValueError
                selected_user = users[user_idx]
                break
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")

        # Backups für den ausgewählten Benutzer anzeigen
        user_backups = [b for b in backups if b['user'] == selected_user]
        if not user_backups:
            print(f"Keine Backups für Benutzer {selected_user} verfügbar.")
            return

        print(f"\nVerfügbare Backups für Benutzer {selected_user}:")
        for idx, backup in enumerate(user_backups, 1):
            size = os.path.getsize(backup['path']) / (1024 * 1024)  # Größe in MB
            print(f"{idx}. {backup['backup']} ({size:.2f} MB)")
        print("0. Abbrechen")

        while True:
            backup_choice = input("Bitte wählen Sie ein Backup zum Wiederherstellen (Nummer, 0 zum Abbrechen): ")
            if backup_choice == '0':
                print("Wiederherstellung abgebrochen.")
                return
            try:
                backup_idx = int(backup_choice) - 1
                if backup_idx < 0 or backup_idx >= len(user_backups):
                    raise ValueError
                selected_backup = user_backups[backup_idx]
                confirm = input(f"Sind Sie sicher, dass Sie das Backup '{selected_backup['backup']}' wiederherstellen möchten? (ja/nein): ")
                if confirm.lower() == 'ja':
                    success = self.backup_manager.restore_backup(selected_backup['path'], selected_user)
                    if success:
                        print("Restore erfolgreich abgeschlossen.")
                    else:
                        print("Restore fehlgeschlagen. Siehe Logs für Details.")
                    return
                else:
                    print("Wiederherstellung abgebrochen.")
                    return
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")


    def restore_file(self):
        backups = self.backup_manager.list_backups()
        if not backups:
            print("Keine Backups verfügbar.")
            return

        print("\nVerfügbare Backups:")
        for idx, backup in enumerate(backups, 1):
            print(f"{idx}. {backup}")

        backup_choice = input("Bitte wählen Sie ein Backup zum Durchsuchen (Nummer): ")
        try:
            idx = int(backup_choice) - 1
            if idx < 0 or idx >= len(backups):
                raise ValueError
            backup_name = backups[idx]
            search_query = input("Bitte geben Sie den Dateinamen oder einen Teil davon ein: ")
            matching_files = self.backup_manager.search_file_in_backup(backup_name, search_query)
            if not matching_files:
                print("Keine passenden Dateien gefunden.")
                return

            print("\nGefundene Dateien:")
            for idx, file in enumerate(matching_files, 1):
                print(f"{idx}. {file}")

            file_choice = input("Bitte wählen Sie eine Datei zum Wiederherstellen (Nummer): ")
            file_idx = int(file_choice) - 1
            if file_idx < 0 or file_idx >= len(matching_files):
                raise ValueError
            file_path = matching_files[file_idx]
            confirm = input(f"Sind Sie sicher, dass Sie die Datei '{file_path}' wiederherstellen möchten? (ja/nein): ")
            if confirm.lower() == 'ja':
                success = self.backup_manager.restore_file_from_backup(backup_name, file_path)
                if success:
                    print("Datei erfolgreich wiederhergestellt.")
                else:
                    print("Wiederherstellung fehlgeschlagen. Siehe Logs für Details.")
        except ValueError:
            print("Ungültige Auswahl.")

    def settings_menu(self):
        while True:
            print("\nEinstellungen:")
            print(f"1. NFS-Mount-Punkt: {self.config.nfs_mount_point}")
            print(f"2. Aufbewahrungszeit in Tagen: {self.config.retention_days}")
            print(f"3. Discord Webhook URL: {'[gesetzt]' if self.config.discord_webhook_url else '[nicht gesetzt]'}")
            print(f"4. Backups komprimieren: {'Ja' if self.config.compress_backups else 'Nein'}")
            print("5. Zurück zum Hauptmenü")
            choice = input("Bitte wählen Sie eine Option zum Ändern: ")

            if choice == '1':
                self.change_nfs_mount_point()
            elif choice == '2':
                self.change_retention_days()
            elif choice == '3':
                self.change_discord_webhook_url()
            elif choice == '4':
                self.toggle_compression()
            elif choice == '5':
                break
            else:
                print("Ungültige Auswahl.")

    def change_nfs_mount_point(self):
        nfs_mount_point = input(f"Neuer NFS-Mount-Punkt [{self.config.nfs_mount_point}]: ") or self.config.nfs_mount_point
        self.config.nfs_mount_point = nfs_mount_point
        self.config.save_config()
        self.backup_manager.nfs_mount_point = nfs_mount_point
        print("NFS-Mount-Punkt aktualisiert.")

    def change_retention_days(self):
        retention_days = input(f"Neue Aufbewahrungszeit in Tagen [{self.config.retention_days}]: ") or self.config.retention_days
        self.config.retention_days = int(retention_days)
        self.config.save_config()
        self.backup_manager.retention_days = int(retention_days)
        print("Aufbewahrungszeit aktualisiert.")

    def change_discord_webhook_url(self):
        webhook_url = input("Neue Discord Webhook URL (leer lassen zum Entfernen): ")
        self.config.discord_webhook_url = webhook_url.strip()
        self.config.save_config()
        self.notifier.webhook_url = self.config.discord_webhook_url
        if self.config.discord_webhook_url:
            print("Discord Webhook URL aktualisiert.")
        else:
            print("Discord Benachrichtigungen deaktiviert.")

    def toggle_compression(self):
        compress = input(f"Backups komprimieren? (ja/nein) [{'ja' if self.config.compress_backups else 'nein'}]: ")
        if compress.lower() == 'ja':
            self.config.compress_backups = True
        else:
            self.config.compress_backups = False
        self.config.save_config()
        self.backup_manager.compress_backups = self.config.compress_backups
        print(f"Komprimierung {'aktiviert' if self.config.compress_backups else 'deaktiviert'}.")

    def exit_program(self):
        confirm = input("Sind Sie sicher, dass Sie das Programm beenden möchten? (ja/nein): ")
        if confirm.lower() == 'ja':
            print("Programm wird beendet.")
            self.scheduler.stop()
            sys.exit()