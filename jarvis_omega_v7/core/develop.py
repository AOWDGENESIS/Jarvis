"""
core/develop.py â€” JARVIS OMNI v7.6 OMEGA
A8: Develop-Modus â€” Jarvis entwickelt sich auf Befehl weiter.
Workflow: Befehl â†’ Code generieren â†’ anzeigen â†’ bestaetigen â†’ speichern.
Rollback bei jedem Schritt moeglich.
"""
import os
import shutil
import logging
import hashlib
from datetime import datetime

log = logging.getLogger("jarvis.develop")

_BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKUP  = os.path.join(_BASE, "data", "backups")

# Aktueller Develop-State (ein Vorschlag gleichzeitig)
_state: dict = {
    "pending":     False,   # Wartet auf Bestaetigung
    "file_path":   None,    # Zieldatei
    "code":        None,    # Generierter Code
    "description": None,    # Was geaendert wird
    "backup_path": None,    # Backup der alten Datei
}


def get_state() -> dict:
    return dict(_state)


def propose_code(file_path: str, code: str, description: str) -> bool:
    """
    Stellt Code-Aenderung zur Bestaetigung bereit.
    Erstellt automatisch ein Backup der Originaldatei.
    """
    global _state

    abs_path = os.path.join(_BASE, file_path)

    # Backup erstellen
    os.makedirs(_BACKUP, exist_ok=True)
    backup_name = f"{os.path.basename(file_path)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    backup_path = os.path.join(_BACKUP, backup_name)

    if os.path.exists(abs_path):
        shutil.copy2(abs_path, backup_path)
        log.info(f"[Develop] Backup erstellt: {backup_path}")

    _state = {
        "pending":     True,
        "file_path":   abs_path,
        "code":        code,
        "description": description,
        "backup_path": backup_path,
    }
    return True


def confirm_and_apply() -> tuple[bool, str]:
    """
    Bestaetigt und schreibt den vorgeschlagenen Code.
    Gibt (success, message) zurueck.
    """
    global _state
    if not _state["pending"]:
        return False, "Kein ausstehender Code-Vorschlag."

    try:
        os.makedirs(os.path.dirname(_state["file_path"]), exist_ok=True)
        with open(_state["file_path"], "w", encoding="utf-8") as f:
            f.write(_state["code"])

        sha = hashlib.sha256(_state["code"].encode()).hexdigest()[:12]
        log.info(f"[Develop] Code geschrieben: {_state['file_path']} (sha:{sha})")

        desc = _state["description"]
        _state = {"pending": False, "file_path": None, "code": None,
                  "description": None, "backup_path": None}
        return True, f"Erfolgreich geschrieben. SHA: {sha}"
    except Exception as e:
        log.error(f"[Develop] Schreiben fehlgeschlagen: {e}")
        return False, f"Fehler beim Schreiben: {e}"


def rollback() -> tuple[bool, str]:
    """Stellt die Backup-Datei wieder her."""
    global _state
    backup = _state.get("backup_path")
    target = _state.get("file_path")

    if not backup or not os.path.exists(backup):
        return False, "Kein Backup verfuegbar."

    try:
        shutil.copy2(backup, target)
        log.info(f"[Develop] Rollback: {backup} -> {target}")
        _state["pending"] = False
        return True, "Rollback erfolgreich. Original wiederhergestellt."
    except Exception as e:
        return False, f"Rollback fehlgeschlagen: {e}"


def reject() -> str:
    """Verwirft den Vorschlag ohne Aenderungen."""
    global _state
    _state = {"pending": False, "file_path": None, "code": None,
              "description": None, "backup_path": None}
    return "Vorschlag verworfen. Keine Aenderungen vorgenommen."


def list_backups() -> list:
    """Listet alle vorhandenen Backups."""
    if not os.path.exists(_BACKUP):
        return []
    return sorted([
        f for f in os.listdir(_BACKUP) if f.endswith(".bak")
    ], reverse=True)


DEVELOP_TRIGGERS = [
    "jarvis develop:", "develop:", "erweitere dich",
    "bau dir selbst", "fueg hinzu:", "neue funktion:",
    "verbessere dich", "update dich",
]


def is_develop_command(prompt: str) -> bool:
    p = prompt.lower().strip()
    return any(t in p for t in DEVELOP_TRIGGERS)


def extract_develop_request(prompt: str) -> str:
    """Extrahiert den eigentlichen Entwicklungswunsch."""
    p = prompt
    for t in DEVELOP_TRIGGERS:
        idx = p.lower().find(t)
        if idx != -1:
            return p[idx + len(t):].strip()
    return p