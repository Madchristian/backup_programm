# Backup-Programm

Ein Python-Programm zum Sichern von `/home`-Verzeichnissen mit Unterstützung für automatische Backups, Fortschrittsanzeige und mehr.

## **Funktionen**

- **Automatische Backups**: Planen Sie Backups zu bestimmten Zeiten.
- **Fortschrittsanzeige**: Verfolgen Sie den Fortschritt mit Restzeitanzeige und aktuellen Dateiinfos.
- **Benachrichtigungen**: Erhalten Sie Benachrichtigungen über Discord-Webhooks.
- **CLI-Menü**: Intuitive Benutzeroberfläche zur Steuerung des Programms.
- **Wiederherstellung**: Stellen Sie vollständige Backups oder einzelne Dateien wieder her.

## **Voraussetzungen**

- Python 3
- Virtuelle Umgebung (`venv`)
- Installierte Pakete aus `requirements.txt`

## **Installation**

1. **Repository klonen:**

   ```bash
   git clone https://github.com/madchristian/backup_programm.git
   cd backup_programm
   ```

2. **Virtuelle Umgebung erstellen und aktivieren:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Installationsskript ausführen (falls vorhanden):**

   ```bash
   ./install.sh
   ```

## **Verwendung**

Starten Sie das Programm mit:

```bash
sudo ./run_backup_program.sh
```

Folgen Sie den Anweisungen im Menü.

## **Konfiguration**

Passen Sie die Einstellungen in `backup_config.ini` an, um z. B. den NFS-Mount-Punkt oder die Aufbewahrungszeit zu ändern.

**Beispiel für die `backup_config.ini`:**

```ini
[DEFAULT]
nfs_mount_point = /mnt/backups
retention_days = 7
backup_hour = 2
backup_minute = 0
discord_webhook_url = https://discord.com/api/webhooks/...
compress_backups = yes
```

## **Funktionen im Detail**

### **Automatische Backups konfigurieren**

- Im Hauptmenü Option `2` auswählen.
- Backup-Zeit (Stunde und Minute) einstellen.
- Das Programm führt automatisch Backups zur eingestellten Zeit durch.

### **Backup jetzt starten**

- Im Hauptmenü Option `1` auswählen.
- Ein manuelles Backup wird sofort gestartet.

### **Restore durchführen**

- Im Hauptmenü Option `3` auswählen.
- Wählen Sie das gewünschte Backup aus der Liste aus.
- Bestätigen Sie die Wiederherstellung.

### **Datei wiederherstellen**

- Im Hauptmenü Option `4` auswählen.
- Wählen Sie das gewünschte Backup aus.
- Geben Sie den Dateinamen oder einen Teil davon ein.
- Wählen Sie die Datei aus der Liste der Suchergebnisse aus.
- Bestätigen Sie die Wiederherstellung.

## **Fehlerbehebung**

- **Backup fehlgeschlagen**: Überprüfen Sie die `backup.log`-Datei für detaillierte Fehlermeldungen.
- **NFS-Share nicht gemountet**: Stellen Sie sicher, dass der NFS-Mount-Punkt korrekt konfiguriert und gemountet ist.
- **Berechtigungsprobleme**: Führen Sie das Programm mit `sudo` aus, um ausreichende Berechtigungen zu gewährleisten.

## **Lizenz**

Dieses Projekt steht unter der **Apache-2.0-Lizenz**. Weitere Informationen finden Sie in der [LICENSE](LICENSE)-Datei.

## **Autoren**

- **madchristian** - *Initiale Arbeit* - [madchristian](https://github.com/madchristian)

## **Danksagungen**

- Inspiration und Hilfestellung durch die OpenAI-Community.
- Verwendung von Bibliotheken wie `tqdm`, `colorama` und `requests`.

---

*Hinweis: Stellen Sie sicher, dass alle erforderlichen Pakete installiert sind und das Programm mit ausreichenden Berechtigungen ausgeführt wird. Bei Fragen oder Problemen wenden Sie sich gerne an den Autor.*

```