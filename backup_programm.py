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

init(autoreset=True)


# Logging konfigurieren
logging.basicConfig(
    filename='backup.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

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
                logging.error(f"Fehler beim Senden der Discord-Benachrichtigung: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Ausnahme beim Senden der Discord-Benachrichtigung: {e}")

class BackupManager:
    def __init__(self, nfs_mount_point, retention_days, notifier, compress_backups):
        self.nfs_mount_point = nfs_mount_point
        self.retention_days = retention_days
        self.notifier = notifier
        self.compress_backups = compress_backups

    def backup_homes(self):
        date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        if self.compress_backups:
            backup_filename = f'backup_{date_str}.tar.gz'
            backup_path = os.path.join(self.nfs_mount_point, backup_filename)
        else:
            backup_path = os.path.join(self.nfs_mount_point, f'backup_{date_str}')

        if not os.path.ismount(self.nfs_mount_point):
            logging.error(f'NFS-Share {self.nfs_mount_point} ist nicht gemountet.')
            self.notifier.send_notification(f'🔴 Backup fehlgeschlagen: NFS-Share {self.nfs_mount_point} ist nicht gemountet.')
            return False

        try:
            if self.compress_backups:
                # Komprimiertes Backup mit Fortschrittsanzeige erstellen
                self.create_tar_with_progress(backup_path)
                logging.info(f'Komprimiertes Backup erfolgreich erstellt: {backup_path}')
            else:
                # Unkomprimiertes Backup erstellen
                self.rsync_backup(backup_path)
                logging.info(f'Backup erfolgreich auf {backup_path} erstellt.')

            self.notifier.send_notification(f'🟢 Backup erfolgreich erstellt: {backup_path}')
            return True
        except Exception as e:
            logging.error(f'Backup fehlgeschlagen: {e}')
            self.notifier.send_notification(f'🔴 Backup fehlgeschlagen: {e}')
            return False

    def create_tar_with_progress(self, backup_path):
        home_dir = '/home'
        file_list = []
        total_size = 0

        # Sammeln aller Dateien und Berechnung der Gesamtgröße
        for root, dirs, files in os.walk(home_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
                try:
                    total_size += os.path.getsize(file_path)
                except FileNotFoundError:
                    continue

        with tarfile.open(backup_path, 'w:gz') as tar:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Erstelle Backup") as progress_bar:
                for file_path in file_list:
                    try:
                        arcname = os.path.relpath(file_path, '/')
                        tar.add(file_path, arcname=arcname)
                        # Aktualisieren des Fortschrittsbalkens
                        file_size = os.path.getsize(file_path)
                        progress_bar.update(file_size)
                        progress_bar.set_postfix({'Datei': os.path.basename(file_path)})
                    except PermissionError:
                        logging.warning(f'Zugriff verweigert: {file_path}')
                    except Exception as e:
                        logging.error(f'Fehler beim Hinzufügen von {file_path}: {e}')

    def get_directory_size(self, directory):
        total = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except FileNotFoundError:
                    continue
        return total

    def rsync_backup(self, backup_path):
        subprocess.run(['rsync', '-a', '/home/', backup_path], check=True)

    def rotate_backups(self):
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        for item in os.listdir(self.nfs_mount_point):
            item_path = os.path.join(self.nfs_mount_point, item)
            if item.startswith('backup_'):
                # Datum extrahieren
                date_str = item.replace('backup_', '').replace('.tar.gz', '')
                try:
                    item_date = datetime.strptime(date_str, '%Y-%m-%d_%H-%M-%S')
                    if item_date < cutoff_date:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        logging.info(f'Altes Backup {item_path} gelöscht.')
                        self.notifier.send_notification(f'🟡 Altes Backup gelöscht: {item_path}')
                except ValueError:
                    continue

    def list_backups(self):
        backups = []
        for item in os.listdir(self.nfs_mount_point):
            if item.startswith('backup_'):
                backups.append(item)
        backups.sort()
        return backups

    def restore_backup(self):
        backups = self.backup_manager.list_backups()
        if not backups:
            print("Keine Backups verfügbar.")
            return

        print("\nVerfügbare Backups:")
        for idx, backup in enumerate(backups, 1):
            print(f"{idx}. {backup}")
        print("0. Abbrechen")

        while True:
            choice = input("Bitte wählen Sie ein Backup zum Wiederherstellen (Nummer, 0 zum Abbrechen): ")
            if choice == '0':
                print("Wiederherstellung abgebrochen.")
                return
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(backups):
                    raise ValueError
                backup_name = backups[idx]
                confirm = input(f"Sind Sie sicher, dass Sie {backup_name} wiederherstellen möchten? (ja/nein): ")
                if confirm.lower() == 'ja':
                    success = self.backup_manager.restore_backup(backup_name)
                    if success:
                        print("Restore erfolgreich abgeschlossen.")
                    else:
                        print("Restore fehlgeschlagen. Siehe Logs für Details.")
                    return  # Nach erfolgreichem oder fehlgeschlagenem Restore zum Hauptmenü zurückkehren
                else:
                    print("Wiederherstellung abgebrochen.")
                    return
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")


    def search_file_in_backup(self, backup_name, search_query):
        backup_path = os.path.join(self.nfs_mount_point, backup_name)
        matching_files = []
        try:
            if backup_name.endswith('.tar.gz'):
                # Inhalte des Archivs auflisten
                result = subprocess.run(['tar', '-tzf', backup_path], capture_output=True, text=True)
                files = result.stdout.splitlines()
            else:
                # Dateien im Verzeichnis auflisten
                files = []
                for root, dirs, filenames in os.walk(backup_path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, backup_path)
                        files.append(relative_path)

            # Suche nach der Datei
            for file in files:
                if search_query in file:
                    matching_files.append(file)

            return matching_files
        except subprocess.CalledProcessError as e:
            logging.error(f'Suche fehlgeschlagen: {e}')
            return []

    def restore_file(self):
        backups = self.backup_manager.list_backups()
        if not backups:
            print("Keine Backups verfügbar.")
            return
    
        print("\nVerfügbare Backups:")
        for idx, backup in enumerate(backups, 1):
            print(f"{idx}. {backup}")
        print("0. Abbrechen")
    
        while True:
            backup_choice = input("Bitte wählen Sie ein Backup zum Durchsuchen (Nummer, 0 zum Abbrechen): ")
            if backup_choice == '0':
                print("Vorgang abgebrochen.")
                return
            try:
                idx = int(backup_choice) - 1
                if idx < 0 or idx >= len(backups):
                    raise ValueError
                backup_name = backups[idx]
                break
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")
    
        search_query = input("Bitte geben Sie den Dateinamen oder einen Teil davon ein (leer zum Abbrechen): ")
        if not search_query:
            print("Vorgang abgebrochen.")
            return
    
        matching_files = self.backup_manager.search_file_in_backup(backup_name, search_query)
        if not matching_files:
            print("Keine passenden Dateien gefunden.")
            return
    
        print("\nGefundene Dateien:")
        for idx, file in enumerate(matching_files, 1):
            print(f"{idx}. {file}")
        print("0. Abbrechen")
    
        while True:
            file_choice = input("Bitte wählen Sie eine Datei zum Wiederherstellen (Nummer, 0 zum Abbrechen): ")
            if file_choice == '0':
                print("Wiederherstellung abgebrochen.")
                return
            try:
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
                    return
                else:
                    print("Wiederherstellung abgebrochen.")
                    return
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")
    

class Scheduler:
    def __init__(self, backup_manager, backup_time):
        self.backup_manager = backup_manager
        self.backup_time = backup_time
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run_scheduler)
        self.thread.start()

    def run_scheduler(self):
        while not self.stop_event.is_set():
            now = datetime.now()
            run_time = datetime.combine(now.date(), self.backup_time)
            if now >= run_time:
                run_time += timedelta(days=1)
            wait_seconds = (run_time - now).total_seconds()

            # Warte bis zur nächsten geplanten Zeit oder bis das Stop-Event gesetzt ist
            if self.stop_event.wait(timeout=wait_seconds):
                # Stop-Event wurde gesetzt, Thread beenden
                break

            # Backup-Operationen durchführen
            self.backup_manager.backup_homes()
            self.backup_manager.rotate_backups()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()

class Config:
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

class CLI:
    def __init__(self):
        self.config = Config()
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

        print("\nVerfügbare Backups:")
        for idx, backup in enumerate(backups, 1):
            print(f"{idx}. {backup}")

        choice = input("Bitte wählen Sie ein Backup zum Wiederherstellen (Nummer): ")
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(backups):
                raise ValueError
            backup_name = backups[idx]
            confirm = input(f"Sind Sie sicher, dass Sie {backup_name} wiederherstellen möchten? (ja/nein): ")
            if confirm.lower() == 'ja':
                success = self.backup_manager.restore_backup(backup_name)
                if success:
                    print("Restore erfolgreich abgeschlossen.")
                else:
                    print("Restore fehlgeschlagen. Siehe Logs für Details.")
        except ValueError:
            print("Ungültige Auswahl.")

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


if __name__ == '__main__':
    CLI()
