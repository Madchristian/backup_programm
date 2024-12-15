import os
import logging
import subprocess
import tarfile
import socket

from tqdm import tqdm

class BackupManager:
    def __init__(self, nfs_mount_point, retention_days, notifier, compress_backups):
        self.nfs_mount_point = nfs_mount_point
        self.retention_days = retention_days
        self.notifier = notifier
        self.compress_backups = compress_backups

    def backup_homes(self):
        date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        hostname = socket.gethostname()

        # Pfad zum Host-Verzeichnis
        host_dir = os.path.join(self.nfs_mount_point, hostname)

        # Sicherstellen, dass das Host-Verzeichnis existiert
        os.makedirs(host_dir, exist_ok=True)

        # Benutzerverzeichnisse ermitteln
        home_dir = '/home'
        user_dirs = [d for d in os.listdir(home_dir) if os.path.isdir(os.path.join(home_dir, d))]

        for user in user_dirs:
            user_home = os.path.join(home_dir, user)
            user_backup_dir = os.path.join(host_dir, user)
            os.makedirs(user_backup_dir, exist_ok=True)

            if self.compress_backups:
                backup_filename = f'backup_{date_str}.tar.gz'
                backup_path = os.path.join(user_backup_dir, backup_filename)
            else:
                backup_dirname = f'backup_{date_str}'
                backup_path = os.path.join(user_backup_dir, backup_dirname)

            # Überprüfen, ob NFS gemountet ist
            if not os.path.ismount(self.nfs_mount_point):
                logging.error(f'NFS-Share {self.nfs_mount_point} ist nicht gemountet.')
                self.notifier.send_notification(f'🔴 Backup fehlgeschlagen: NFS-Share {self.nfs_mount_point} ist nicht gemountet.')
                return False

            try:
                if self.compress_backups:
                    # Komprimiertes Backup erstellen
                    self.create_tar_with_progress(backup_path, user_home)
                    logging.info(f'Komprimiertes Backup für Benutzer {user} erfolgreich erstellt: {backup_path}')
                else:
                    # Unkomprimiertes Backup erstellen
                    self.rsync_backup(backup_path, user_home)
                    logging.info(f'Backup für Benutzer {user} erfolgreich auf {backup_path} erstellt.')

                self.notifier.send_notification(f'🟢 Backup für Benutzer {user} erfolgreich erstellt: {backup_path}')
            except Exception as e:
                logging.error(f'Backup für Benutzer {user} fehlgeschlagen: {e}')
                self.notifier.send_notification(f'🔴 Backup für Benutzer {user} fehlgeschlagen: {e}')
                return False

        return True



    def create_tar_with_progress(self, backup_path, source_dir):
        file_list = []
        total_size = 0

        # Sammeln aller Dateien und Berechnung der Gesamtgröße
        for root, dirs, files in os.walk(source_dir):
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
                        arcname = os.path.relpath(file_path, source_dir)
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

    def rsync_backup(self, backup_path, source_dir):
        subprocess.run(['rsync', '-a', f'{source_dir}/', backup_path], check=True)

    def rotate_backups(self):
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        hostname = socket.gethostname()
        host_dir = os.path.join(self.nfs_mount_point, hostname)

        if not os.path.exists(host_dir):
            return

        for user in os.listdir(host_dir):
            user_backup_dir = os.path.join(host_dir, user)
            if not os.path.isdir(user_backup_dir):
                continue
            for item in os.listdir(user_backup_dir):
                item_path = os.path.join(user_backup_dir, item)
                # Datum aus dem Backup-Namen extrahieren
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
        host_dir = os.path.join(self.nfs_mount_point, socket.gethostname())
        if not os.path.exists(host_dir):
            return backups

        for user in os.listdir(host_dir):
            user_backup_dir = os.path.join(host_dir, user)
            if not os.path.isdir(user_backup_dir):
                continue
            for backup in os.listdir(user_backup_dir):
                backup_path = os.path.join(user_backup_dir, backup)
                backups.append({
                    'user': user,
                    'backup': backup,
                    'path': backup_path
                })
        # Sortieren der Backups nach Datum (optional)
        backups.sort(key=lambda x: x['backup'])
        return backups


    def restore_backup(self, backup_path):
        if not os.path.exists(backup_path):
            logging.error(f"Backup {backup_path} existiert nicht.")
            self.notifier.send_notification(f"🔴 Restore fehlgeschlagen: Backup {backup_path} existiert nicht.")
            return False

        try:
            if backup_path.endswith('.tar.gz'):
                # Verzeichnisse auslesen und erstellen
                self.ensure_directories_exist(backup_path)

                # Komprimiertes Backup wiederherstellen
                subprocess.run(['tar', '-xzf', backup_path, '-C', '/'], check=True)
                logging.info(f"Backup {backup_path} erfolgreich wiederhergestellt.")
            else:
                # Unkomprimiertes Backup wiederherstellen
                subprocess.run(['rsync', '-a', backup_path + '/', '/home/'], check=True)
                logging.info(f"Backup {backup_path} erfolgreich wiederhergestellt.")

            self.notifier.send_notification(f"🟢 Restore erfolgreich: {backup_path}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Restore fehlgeschlagen: {e}")
            self.notifier.send_notification(f"🔴 Restore fehlgeschlagen: {e}")
            return False

    def ensure_directories_exist(self, backup_path):
        try:
            result = subprocess.run(['tar', '-tf', backup_path], capture_output=True, text=True, check=True)
            directories = set()
            for line in result.stdout.splitlines():
                if line.endswith('/'):
                    directories.add(line.rstrip('/'))

            for directory in sorted(directories):
                full_path = os.path.join('/', directory)
                os.makedirs(full_path, exist_ok=True)
                logging.info(f"Erstelle fehlendes Verzeichnis: {full_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Fehler beim Auslesen der Verzeichnisse aus {backup_path}: {e}")
            raise

    def search_file_in_backup(self, backup, search_query):
        backup_path = backup['path']
        matching_files = []
        try:
            if backup_path.endswith('.tar.gz'):
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
            logging.error(f"Suche fehlgeschlagen: {e}")
            return []


    def restore_file_from_backup(self, backup, file_path):
        backup_path = backup['path']
        try:
            if backup_path.endswith('.tar.gz'):
                # Einzelne Datei aus dem Archiv extrahieren
                subprocess.run(['tar', '-xzf', backup_path, '-C', '/', file_path], check=True)
                logging.info(f"Datei {file_path} erfolgreich aus {backup_path} wiederhergestellt.")
            else:
                # Einzelne Datei mit rsync wiederherstellen
                src_path = os.path.join(backup_path, file_path)
                dest_path = os.path.join('/', file_path)
                dest_dir = os.path.dirname(dest_path)
                os.makedirs(dest_dir, exist_ok=True)
                subprocess.run(['rsync', '-a', src_path, dest_path], check=True)
                logging.info(f"Datei {file_path} erfolgreich aus {backup_path} wiederhergestellt.")

            self.notifier.send_notification(f"🟢 Datei {file_path} erfolgreich wiederhergestellt aus {backup_path}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Wiederherstellung der Datei fehlgeschlagen: {e}")
            self.notifier.send_notification(f"🔴 Wiederherstellung der Datei fehlgeschlagen: {e}")
            return False


    def restore_file(self):
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
                print("Vorgang abgebrochen.")
                return
            try:
                user_idx = int(user_choice) - 1
                if user_idx < 0 or user_idx >= len(users):
                    raise ValueError
                selected_user = users[user_idx]
                break
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")

        # Backups für den ausgewählten Benutzer
        user_backups = [b for b in backups if b['user'] == selected_user]
        if not user_backups:
            print(f"Keine Backups für Benutzer {selected_user} verfügbar.")
            return

        print(f"\nVerfügbare Backups für Benutzer {selected_user}:")
        for idx, backup in enumerate(user_backups, 1):
            print(f"{idx}. {backup['backup']}")
        print("0. Abbrechen")

        while True:
            backup_choice = input("Bitte wählen Sie ein Backup zum Durchsuchen (Nummer, 0 zum Abbrechen): ")
            if backup_choice == '0':
                print("Vorgang abgebrochen.")
                return
            try:
                backup_idx = int(backup_choice) - 1
                if backup_idx < 0 or backup_idx >= len(user_backups):
                    raise ValueError
                selected_backup = user_backups[backup_idx]
                break
            except ValueError:
                print("Ungültige Auswahl. Bitte versuchen Sie es erneut.")

        search_query = input("Bitte geben Sie den Dateinamen oder einen Teil davon ein (leer zum Abbrechen): ")
        if not search_query:
            print("Vorgang abgebrochen.")
            return

        matching_files = self.backup_manager.search_file_in_backup(selected_backup['path'], search_query)
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
                    success = self.backup_manager.restore_file_from_backup(selected_backup['path'], file_path)
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