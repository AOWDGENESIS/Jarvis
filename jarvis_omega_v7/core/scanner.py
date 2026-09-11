"""
core/scanner.py â€” JARVIS OMNI v7.6 OMEGA  (KORRIGIERT)
Findet Ollama auf allen Laufwerken, startet es, und wartet
GARANTIERT bis der HTTP-Port offen und ein Modell geladen ist.

WAS WURDE KORRIGIERT (Fix-2 / Modell-PrioritÃ¤t):
  Die alte PrioritÃ¤tenliste (qwen2.5, gemma2, mistral, ...) sprach die
  ECHTEN Modelle auf diesem System nicht an. Bei "keinem Treffer" wurde
  einfach das erste Modell genommen  ->  konnte das 18-GB-Modell
  gemma4:26b wÃ¤hlen, das NICHT in den VRAM passt  ->  Satelliten-Modus.

  NEU: Auswahl ist GRÃ–SSEN-BEWUSST.
    - Riesen-Modelle (>12 GB) werden Ã¼bersprungen, solange ein kleineres
      Chat-Modell existiert (z. B. llama3:latest mit 4,7 GB).
    - llama3 wird vor gemma4 bevorzugt.
    - Nur wenn GAR kein kleineres Modell da ist, wird das grosse genommen
      (und dann ehrlich gewarnt).
  Die Ã¼brige Startlogik ist unverÃ¤ndert.
"""
import os
import time
import logging
import psutil
import subprocess
import requests

log = logging.getLogger("jarvis.scanner")

# â”€â”€ Globaler State (wird von brain.py gelesen) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
OLLAMA_STATE: dict = {
    "api_ready":        False,
    "best_model":       None,    # Conversation-Brain
    "code_model":       None,    # Code-Brain
    "available_models": [],
    "exe_path":         None,
    "models_path":      None,
}

# Modelle Ã¼ber dieser GrÃ¶ÃŸe (Bytes) gelten als "zu gross zum sicheren Start".
# Sie passen oft nicht in den VRAM -> nie automatisch, solange es Kleineres gibt.
MAX_AUTO_SIZE_BYTES = 12 * 1024 * 1024 * 1024  # 12 GB

# Reine Embedding-Modelle koennen nicht normal reden -> nie als Hauptmodell.
EMBEDDING_HINTS = ("embed", "nomic", "mxbai", "minilm", "e5", "paraphrase")

# PrioritÃ¤t fÃ¼rs GesprÃ¤chs-Brain (Reihenfolge = Wunsch). EXAKT auf Felicias
# echte Modelle abgestimmt (aus `ollama list`, 13 Modelle). Kleine, schnelle
# Modelle zuerst, damit es sicher in den VRAM passt und wirklich antwortet.
_MODEL_PRIORITY = [
    "llama3",            # 4.7 GB  -> universell, passt sicher (Favorit)
    "qwen3",             # 5.2 GB  -> bestes GesprÃ¤chsmodell, schnell
    "gemma2",            # 5.4 GB  -> solide
    "mistral",           # 4.4 GB  -> schnell
    "qwen2.5",           # 9.0 GB  -> stark, aber schwerer
    "llama3.2",          # 2.0 GB  -> Mini (fallback)
]

# Code/Develop-Brain PrioritÃ¤t (exakt auf Felicias echte Code-Modelle)
CODE_MODEL_PRIORITY = [
    "deepseek-coder-v2",   # 8.9 GB  -> bestes Code-Modell (Favorit)
    "deepseek-coder",
    "codellama",           # 3.8 GB  -> kleiner fallback
    "qwen2.5",             # generalist fallback
    "llama3",
]


def _name_low(name: str) -> str:
    return name.lower()


def _is_embedding(name: str) -> bool:
    low = _name_low(name)
    return any(h in low for h in EMBEDDING_HINTS)


def _size_ok(size: int | None) -> bool:
    """GrÃ¶sse unbekannt oder unter der Grenze -> ok zum Auto-WÃ¤hlen."""
    return size is None or size <= MAX_AUTO_SIZE_BYTES


def _pick_best_model(models: list) -> str | None:
    """
    WÃ¤hlt das Conversation-Brain.

    models: Liste von dicts, jeweils {'name', optional 'size'}.
    Logik (GrÃ¶ssen-bewusst):
      1) Wunschliste respektieren, aber Riesen-Modelle Ã¼berspringen.
      2) Sonst: das kleinste verfÃ¼gbare Chat-Modell unter der GrÃ¶ssengrenze.
      3) Nur wenn gar nichts Kleineres existiert: das kleinste Modell (mit
         Warnung).
    """
    # Chat-Modelle (ohne Embedding), mit grÃ¶sse, sammeln
    chat = []
    for m in models:
        if not isinstance(m, dict):
            continue
        name = m.get("name")
        if not name or _is_embedding(name):
            continue
        chat.append((name, m.get("size")))

    if not chat:
        return None

    # 1) Wunschliste respektieren (Reihenfolge), Riesen-Modelle Ã¼berspringen.
    for prio in _MODEL_PRIORITY:
        for name, size in chat:
            low = _name_low(name)
            if prio in low and _size_ok(size):
                return name

    # 2) Kleinste Chat-Modell, das unter der Grenze liegt.
    small = [x for x in chat if x[1] is not None and x[1] <= MAX_AUTO_SIZE_BYTES]
    if small:
        small.sort(key=lambda x: x[1])
        return small[0][0]

    # 3) Alles zu gross oder unbekannt -> kleinstes, mit ehrlicher Warnung.
    definite = [x for x in chat if x[1] is not None]
    if definite:
        definite.sort(key=lambda x: x[1])
        chosen = definite[0][0]
        log.warning(
            f"[Scanner] Nur grosse Modelle verfÃ¼gbar â†’ wÃ¤hle '{chosen}'. "
            f"Kann sein, dass es nicht in den VRAM passt (Satelliten-Modus)."
        )
        return chosen
    # GrÃ¶ÃŸe komplett unbekannt -> erstes Chat-Modell als sichere Annahme.
    log.warning("[Scanner] ModellgrÃ¶ssen unbekannt â†’ wÃ¤hle erstes Chat-Modell.")
    return chat[0][0]


def _pick_code_model(names: list) -> str | None:
    """WÃ¤hlt Code/Develop-Brain aus PrioritÃ¤tsliste."""
    lower_map = {n.lower(): n for n in names}
    for prio in CODE_MODEL_PRIORITY:
        for low, orig in lower_map.items():
            if prio in low:
                return orig
    return None  # kein Code-Model â†’ fÃ¤llt auf Conversation-Brain zurÃ¼ck


def _update_state_from_api() -> bool:
    """Fragt /api/tags ab und befÃ¼llt OLLAMA_STATE. Gibt True zurÃ¼ck wenn OK."""
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200:
            raw = r.json().get("models", []) or []
            names = []
            models_info = []
            for m in raw:
                name = m.get("name")
                if not name:
                    continue
                names.append(name)
                models_info.append({"name": name, "size": m.get("size")})  # size in bytes
            OLLAMA_STATE["api_ready"]        = True
            OLLAMA_STATE["available_models"] = names
            OLLAMA_STATE["best_model"]       = _pick_best_model(models_info)
            OLLAMA_STATE["code_model"]       = _pick_code_model(names)
            log.info(
                f"[Scanner] Modelle gefunden: {names} â†’ "
                f"GesprÃ¤ch='{OLLAMA_STATE['best_model']}', "
                f"Code='{OLLAMA_STATE['code_model']}'"
            )
            return True
    except Exception:
        pass
    return False


def _wait_for_api(timeout_sec: int = 90) -> bool:
    """
    Pollt Ollama /api/tags bis zu timeout_sec Sekunden.
    Gibt True zurÃ¼ck sobald die API antwortet.
    """
    log.info(f"[Scanner] Warte auf Ollama API (max {timeout_sec}s)...")
    deadline = time.monotonic() + timeout_sec
    attempt  = 0

    while time.monotonic() < deadline:
        attempt += 1
        if _update_state_from_api():
            log.info(
                f"[Scanner] âœ“ Ollama API bereit nach ~{attempt * 2}s. "
                f"Verwende: '{OLLAMA_STATE['best_model']}'"
            )
            return True
        time.sleep(2)

    log.error("[Scanner] âœ— Ollama API hat nicht innerhalb des Timeouts geantwortet.")
    return False


def _count_model_manifests(models_dir: str | None) -> int:
    """ZÃ¤hlt Modell-Manifeste unter <dir>\\manifests\\registry.ollama.ai\\library\\**.
    Je mehr Manifeste, desto vollstÃ¤ndiger/korrekter ist der Modellordner.
    Ein kaputt verschachtelter Ordner (manifests nur teilweise, Blobs falsch
    abgelegt) hat wenige/-null Manifeste und wird dadurch NICHT gewÃ¤hlt."""
    if not models_dir:
        return 0
    base = os.path.join(models_dir, "manifests", "registry.ollama.ai", "library")
    count = 0
    try:
        for _root, _dirs, files in os.walk(base):
            count += len(files)
    except Exception:
        pass
    return count


def _pick_best_models_dir(candidates: list) -> str | None:
    """WÃ¤hlt aus mehreren Kandidaten den VOLLSTÃ„NDIGSTEN Modellordner
    (meiste Manifeste). Bevorzugt so z. B. den korrekten Standard-Ordner
    gegenÃ¼ber einem kaputt verschachtelten Laufwerks-Ordner."""
    best = None
    best_count = -1
    for c in candidates:
        n = _count_model_manifests(c)
        if n > best_count:
            best_count = n
            best = c
    return best


def omni_scanner() -> bool:
    """
    1. PrÃ¼ft ob Ollama schon lÃ¤uft (bereits installiert/aktiv).
    2. Sucht ollama.exe auf allen Festplatten.
    3. Startet Ollama und wartet bis API + Modell bereit.
    Gibt True zurÃ¼ck wenn Ollama nach dem Aufruf einsatzbereit ist.
    """

    # â”€â”€ Schritt 1: Vielleicht lÃ¤uft Ollama schon â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if _update_state_from_api():
        log.info("[Scanner] Ollama lÃ¤uft bereits â€“ kein Neustart nÃ¶tig.")
        if not OLLAMA_STATE["best_model"]:
            log.warning("[Scanner] Kein Modell in Ollama gefunden! Bitte 'ollama pull llama3' ausfÃ¼hren.")
            return False
        return True

    # â”€â”€ Schritt 2: Ollama-Exe auf allen Laufwerken suchen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    found_exe    = None
    model_candidates = []   # mehrere Kandidaten sammeln, dann besten wÃ¤hlen

    try:
        drives = [d.device for d in psutil.disk_partitions() if "fixed" in d.opts]
    except Exception as e:
        log.warning(f"[Scanner] Laufwerk-Scan Fehler: {e}")
        drives = ["C:\\"]

    # Der Standard-Ordner ist fast immer der korrekte/vollstÃ¤ndigste.
    home_models = os.path.join(os.path.expanduser("~"), ".ollama", "models")
    if os.path.isdir(home_models):
        model_candidates.append(home_models)

    for drive in drives:
        if not found_exe:
            candidate = os.path.join(drive, "Ollama", "ollama.exe")
            if os.path.isfile(candidate):
                found_exe = candidate
                OLLAMA_STATE["exe_path"] = found_exe
                log.info(f"[Scanner] ollama.exe gefunden: {found_exe}")

        candidate = os.path.join(drive, "OllamaModels")
        if os.path.isdir(candidate):
            model_candidates.append(candidate)

    # VollstÃ¤ndigsten (meiste Manifeste) Modellordner wÃ¤hlen.
    found_models = _pick_best_models_dir(model_candidates)
    if found_models:
        OLLAMA_STATE["models_path"] = found_models
        log.info(
            f"[Scanner] Beste Modell-Ablage: {found_models} "
            f"({_count_model_manifests(found_models)} Modelle)"
        )

    # Modell-Pfad setzen bevor Ollama startet (nur der beste, nicht der kaputte).
    if found_models:
        os.environ["OLLAMA_MODELS"] = found_models
        log.info(f"[Scanner] OLLAMA_MODELS = {found_models}")

    # â”€â”€ Schritt 3: Alte Ollama-Prozesse sauber beenden â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "ollama" in proc.info["name"].lower():
                proc.kill()
                log.info(f"[Scanner] Alter Ollama-Prozess PID {proc.pid} beendet.")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    time.sleep(1.5)  # Port freigeben lassen

    # â”€â”€ Schritt 4: Ollama starten â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    launch_cmd = [found_exe, "serve"] if found_exe else ["ollama", "serve"]

    try:
        # CREATE_NO_WINDOW existiert nur unter Windows; robust zugreifen.
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            launch_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        log.info(f"[Scanner] Ollama gestartet (PID {proc.pid}): {' '.join(launch_cmd)}")
    except FileNotFoundError:
        log.error("[Scanner] âœ— Ollama nicht gefunden. Bitte von https://ollama.ai installieren.")
        return False
    except Exception as e:
        log.error(f"[Scanner] Start-Fehler: {e}")
        return False

    # â”€â”€ Schritt 5: Warten bis HTTP API antwortet â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ready = _wait_for_api(timeout_sec=90)

    if ready and not OLLAMA_STATE["best_model"]:
        log.warning(
            "[Scanner] Ollama lÃ¤uft, aber KEIN Modell installiert! "
            "Bitte im Terminal ausfÃ¼hren: ollama pull llama3"
        )
        return False

    return ready