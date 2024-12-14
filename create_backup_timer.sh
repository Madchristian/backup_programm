#!/bin/bash

SERVICE_NAME="backup_program.service"
TIMER_NAME="backup_program.timer"
TIMER_FILE="/etc/systemd/system/$TIMER_NAME"

# Uhrzeit für das automatische Backup
BACKUP_HOUR="02"  # Stunden (24-Stunden-Format)
BACKUP_MINUTE="00" # Minuten

echo "Erstelle systemd-Timer für den automatisierten Backup-Dienst..."

# Inhalt des Timer-Files erstellen
sudo bash -c "cat > $TIMER_FILE" << EOL
[Unit]
Description=Timer für automatisierte Backups

[Timer]
OnCalendar=*-*-* ${BACKUP_HOUR}:${BACKUP_MINUTE}:00
Persistent=true

[Install]
WantedBy=timers.target
EOL

# systemd-Timer aktivieren und starten
echo "Aktiviere und starte den Timer..."
sudo systemctl daemon-reload
sudo systemctl enable $TIMER_NAME
sudo systemctl start $TIMER_NAME

# Timer-Status anzeigen
echo "Timer wurde erfolgreich erstellt und aktiviert. Details:"
systemctl list-timers | grep $TIMER_NAME
