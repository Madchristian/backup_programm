#!/bin/bash

# Installationsskript für das Backup-Programm
# Unterstützte Distributionen: Debian/Ubuntu, CentOS/RHEL, Fedora

# Funktion zur Installation auf Debian/Ubuntu
install_debian() {
    echo "Erkenne Debian/Ubuntu-basierte Distribution..."

    # Update Paketlisten
    sudo apt-get update

    # Installiere erforderliche Systempakete
    sudo apt-get install -y python3 python3-pip rsync nfs-common

    # Installiere Python-Abhängigkeiten
    pip3 install requests

    echo "Alle Abhängigkeiten wurden erfolgreich installiert (Debian/Ubuntu)."
}

# Funktion zur Installation auf CentOS/RHEL
install_centos() {
    echo "Erkenne CentOS/RHEL-basierte Distribution..."

    # Update Paketlisten
    sudo yum update -y

    # Installiere erforderliche Systempakete
    sudo yum install -y python3 python3-pip rsync nfs-utils

    # Installiere Python-Abhängigkeiten
    pip3 install requests

    echo "Alle Abhängigkeiten wurden erfolgreich installiert (CentOS/RHEL)."
}

# Funktion zur Installation auf Fedora
install_fedora() {
    echo "Erkenne Fedora-basierte Distribution..."

    # Update Paketlisten
    sudo dnf update -y

    # Installiere erforderliche Systempakete
    sudo dnf install -y python3 python3-pip rsync nfs-utils

    # Installiere Python-Abhängigkeiten
    pip3 install requests

    echo "Alle Abhängigkeiten wurden erfolgreich installiert (Fedora)."
}

# Hauptinstallationsroutine
if [ -f /etc/debian_version ]; then
    install_debian
elif [ -f /etc/redhat-release ]; then
    if grep -q "CentOS" /etc/redhat-release; then
        install_centos
    elif grep -q "Fedora" /etc/redhat-release; then
        install_fedora
    else
        echo "Red Hat-basierte Distribution erkannt, versuche Installation..."
        install_centos
    fi
else
    echo "Ihre Linux-Distribution wird nicht automatisch unterstützt."
    echo "Bitte installieren Sie die folgenden Pakete manuell:"
    echo "- python3"
    echo "- python3-pip"
    echo "- rsync"
    echo "- NFS-Tools (nfs-common oder nfs-utils)"
    echo "Und führen Sie dann 'pip3 install requests' aus."
fi
