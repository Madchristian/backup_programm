#!/bin/bash

VENV_DIR="venv"

# Prüfen, ob die virtuelle Umgebung existiert
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtuelle Umgebung nicht gefunden. Bitte führen Sie das Installationsskript aus."
    exit 1
fi

# Virtuelle Umgebung aktivieren
source $VENV_DIR/bin/activate

# Argumente überprüfen
if [[ "$1" == "--service" ]]; then
    echo "Starte das Backup-Programm im Service-Modus..."
    python3 main.py --service
else
    echo "Starte das Backup-Programm im interaktiven Modus..."
    python3 main.py
fi
