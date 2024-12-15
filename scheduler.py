import threading
from datetime import datetime, timedelta

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