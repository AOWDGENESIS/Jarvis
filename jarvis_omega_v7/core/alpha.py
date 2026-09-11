"""
core/alpha.py â€” JARVIS OMNI v7.6 OMEGA
A5/D1: Alpha-Protokoll â€” Sicherheitslayer
Schuetzt Felix, blockiert gefaehrliche Befehle, erkennt Krisen.
"""
import logging
import os
import hashlib
import json
from datetime import datetime

log = logging.getLogger("jarvis.alpha")

# â”€â”€ Gesperrte Befehle (D4-konform) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BLOCKED_COMMANDS = [
    "format c:", "rm -rf", "del /f /s", "shutdown", "taskkill /f",
    "reg delete", "net user", "bcdedit", "diskpart",
    "drop table", "delete from", "truncate",
]

# â”€â”€ Sicherheits-Log Pfad â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECURITY_LOG = os.path.join(_BASE, "data", "security.log")


def _write_log(event: str, detail: str, severity: str = "INFO"):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "severity":  severity,
        "event":     event,
        "detail":    detail,
    }
    try:
        with open(SECURITY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        log.warning(f"[Alpha] Security-Log Fehler: {e}")


def check_command(prompt: str) -> tuple[bool, str]:
    """
    Prueft ob ein Befehl erlaubt ist.
    Gibt (allowed: bool, reason: str) zurueck.
    """
    p = prompt.lower()

    for blocked in BLOCKED_COMMANDS:
        if blocked in p:
            reason = f"Blockierter Befehl erkannt: '{blocked}'"
            _write_log("BLOCKED", reason, "WARNING")
            log.warning(f"[Alpha] {reason}")
            return False, f"Dieser Befehl ist gesperrt ({blocked}). Alpha-Protokoll aktiv."

    # Pfad-Traversal Erkennung
    if "../" in prompt or "..\\" in prompt:
        _write_log("PATH_TRAVERSAL", prompt[:100], "WARNING")
        return False, "Pfad-Traversal erkannt. Zugriff verweigert."

    # Injection-Erkennung
    danger_patterns = ["eval(", "exec(", "os.system(", "subprocess.call(", "__import__"]
    for pat in danger_patterns:
        if pat in prompt:
            _write_log("INJECTION", pat, "HIGH")
            return False, f"Potenziell gefaehrlicher Ausdruck erkannt. Bitte anders formulieren."

    return True, ""


def log_interaction(role: str, content: str, mode: str = ""):
    """Protokolliert jede Interaktion im Security-Log (Audit-Trail)."""
    _write_log("INTERACTION", f"[{mode}] {role}: {content[:200]}", "INFO")


def get_security_report() -> dict:
    """Erstellt einen Sicherheitsbericht."""
    warnings = errors = interactions = 0
    try:
        with open(SECURITY_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    sev = entry.get("severity", "")
                    if sev == "WARNING": warnings += 1
                    elif sev == "HIGH":  errors += 1
                    else:                interactions += 1
                except Exception:
                    pass
    except FileNotFoundError:
        pass

    return {
        "interactions": interactions,
        "warnings":     warnings,
        "blocked":      errors,
        "log_path":     SECURITY_LOG,
        "status":       "AKTIV" if os.path.exists(SECURITY_LOG) else "KEIN LOG",
    }


# Alpha-Protokoll beim Import aktivieren
log.info("[Alpha] Alpha-Protokoll v1.0 aktiv â€” Sicherheitslayer bereit.")