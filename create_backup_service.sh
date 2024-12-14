#!/bin/bash

SERVICE_FILE="/etc/systemd/system/backup_program.service"

echo "Erstelle Systemdienst für das Backup-Programm..."

# Inhalt des Dienstes
sudo bash -c "cat > $SERVICE_FILE" << EOL
[Unit]
Description=Automatisierter Backup Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/run_backup_service.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# systemd aktualisieren und Dienst aktivieren
sudo systemctl daemon-reload
sudo systemctl enable backup_program.service
sudo systemctl start backup_program.service

echo "Systemdienst wurde eingerichtet und gestartet."
