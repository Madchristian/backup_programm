#!/bin/bash

VENV_DIR="venv"

# Prüfen, ob die virtuelle Umgebung existiert
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtuelle Umgebung nicht gefunden. Bitte führen Sie das Installationsskript aus."
    exit 1
fi

# Virtuelle Umgebung aktivieren
source $VENV_DIR/bin/activate

# Backup-Programm im Service-Modus starten
python3 backup_programm.py --service