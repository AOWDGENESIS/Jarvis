"""
main.py â€” JARVIS OMNI v7.6 OMEGA
Startup-Sequenz: Scanner â†’ Warten â†’ Warmup â†’ Server.
Status-Endpunkt gibt echten Modus zurÃ¼ck: EINSTEIN / LOADING / SATELLITE.
"""
import os
import logging
import threading
import socket
import webbrowser
import time
import psutil
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from core.brain import EinsteinCore
from core import alpha as jarvis_alpha
from core import develop as jarvis_develop
from core import db as jarvis_db
from core.voice import jarvis_voice, edge_voice, piper_voice, pyttsx3_voice, EDGE_VOICES_DE
from core.scanner import omni_scanner, OLLAMA_STATE

PORT = 8000

# â”€â”€ Logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis.main")

# â”€â”€ App & Brain â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app   = FastAPI(title="Jarvis OMNI v7.6")

# I3/I5: Datenbank initialisieren
jarvis_db.init_db()
brain = EinsteinCore()

# â”€â”€ API-Routen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/api/status")
async def get_status():
    """
    Gibt den echten Betriebsmodus zurÃ¼ck.
    EINSTEIN  â†’ Ollama lÃ¤uft, Modell warm, ready.
    LOADING   â†’ Ollama API antwortet, aber Modell noch nicht warm.
    SATELLITE â†’ Ollama nicht erreichbar.
    """
    if brain.is_ready():
        mode  = "EINSTEIN"
        color = "#00ff88"
    elif OLLAMA_STATE["api_ready"]:
        mode  = "LOADING"
        color = "#ff9d00"
    else:
        mode  = "SATELLITE"
        color = "#ff4444"

    return {
        "einstein":       mode,
        "einstein_color": color,
        "model":          OLLAMA_STATE.get("best_model") or "â€”",
        "code_model":     OLLAMA_STATE.get("code_model") or "â€”",
        "cpu":            psutil.cpu_percent(),
        "ram":            psutil.virtual_memory().percent,
    }


@app.post("/api/command")
async def handle_command(request: Request):
    data       = await request.json()
    user_input = data.get("command", "").strip()

    if not user_input:
        return {"response": "Kein Befehl empfangen.", "mode": "SATELLITE"}

    # "vergiss alles" / "reset" â†’ History lÃ¶schen (C10)
    if any(w in user_input.lower() for w in ["vergiss alles", "reset gesprÃ¤ch", "neues gesprÃ¤ch"]):
        brain.clear_history()
        return {"response": "GesprÃ¤chsverlauf gelÃ¶scht. Ich bin bereit fÃ¼r einen neuen Start, Master Felix.", "mode": "EINSTEIN"}

    # A5/D1: Alpha-Protokoll Check
    allowed, reason = jarvis_alpha.check_command(user_input)
    if not allowed:
        return {"response": f"Alpha-Protokoll: {reason}", "mode": "SATELLITE"}

    jarvis_alpha.log_interaction("Felix", user_input)
    reply, mode = brain.query(user_input)
    jarvis_alpha.log_interaction("Jarvis", reply, mode)
    # E4: Backend spielt NICHT mehr direkt â€” Frontend erhÃ¤lt Text und ruft /api/tts ab
    return {"response": reply, "mode": mode}


@app.post("/api/tts")
async def text_to_speech(request: Request):
    """
    E2/E6: Generiert MP3 via Edge-TTS und gibt Audio-Bytes zurÃ¼ck.
    Frontend spielt ab â€” E4 garantiert (nur EINE Audio-Quelle).
    """
    import asyncio
    data  = await request.json()
    text  = data.get("text",  "").strip()
    voice = data.get("voice", "de-DE-KatjaNeural")
    rate  = data.get("rate",  "+0%")

    if not text:
        return Response(status_code=400)

    if not edge_voice.is_available():
        # Edge-TTS nicht installiert â†’ leere Response â†’ Frontend fÃ¤llt auf Browser-TTS zurÃ¼ck
        log.warning("[TTS] edge-tts nicht verfÃ¼gbar â€” Frontend nutzt Browser-Fallback.")
        return Response(status_code=503, content=b"", media_type="audio/mpeg")

    audio_bytes = await edge_voice.synthesize_async(text, voice=voice, rate=rate)

    if not audio_bytes:
        return Response(status_code=503, content=b"", media_type="audio/mpeg")

    return Response(
        content      = audio_bytes,
        media_type   = "audio/mpeg",
        headers      = {"Cache-Control": "no-cache"},
    )


@app.get("/api/voices")
async def get_voices():
    """Gibt alle verfÃ¼gbaren deutschen Edge-TTS Stimmen zurÃ¼ck."""
    piper_voices = [
        {"id": f"piper:{v}", "label": f"ðŸ  {v} (Lokal)", "gender": "M"}
        for v in piper_voice.get_voices()
    ]
    return {
        "voices":        piper_voices + EDGE_VOICES_DE,
        "default":       f"piper:{piper_voice.DEFAULT_VOICE}" if piper_voice.is_available() else "de-DE-KatjaNeural",
        "edge_tts_ok":   edge_voice.is_available(),
        "piper_ok":      piper_voice.is_available(),
        "piper_voices":  piper_voice.get_voices(),
    }


@app.delete("/api/history")
async def clear_history():
    """LÃ¶scht den GesprÃ¤chsverlauf (C10)."""
    brain.clear_history()
    return {"ok": True}


@app.get("/api/tasks")
async def get_tasks():
    """I3: Alle offenen Aufgaben."""
    return {"tasks": jarvis_db.get_open_tasks()}


@app.post("/api/tasks")
async def create_task(request: Request):
    """I3: Neue Aufgabe direkt erstellen."""
    data = await request.json()
    text = data.get("text", "").strip()
    reminder_str = data.get("reminder_dt")
    if not text:
        return {"error": "Kein Text angegeben"}
    from datetime import datetime
    reminder_dt = datetime.fromisoformat(reminder_str) if reminder_str else None
    task_id = jarvis_db.add_task(text, reminder_dt)
    return {"id": task_id, "text": text}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    """I3: Aufgabe lÃ¶schen."""
    jarvis_db.delete_task(task_id)
    return {"ok": True}


@app.patch("/api/tasks/{task_id}/done")
async def complete_task(task_id: int):
    """I3: Aufgabe als erledigt markieren."""
    jarvis_db.complete_task(task_id)
    return {"ok": True}


@app.get("/api/history/load")
async def load_history():
    """I5: Letzte Nachrichten aus DB laden."""
    msgs = jarvis_db.load_recent_messages(limit=30)
    stats = jarvis_db.get_conversation_stats()
    return {"messages": msgs, "stats": stats}


@app.get("/api/reminders/check")
async def check_reminders():
    """I3: FÃ¤llige Erinnerungen prÃ¼fen (wird vom Frontend alle 30s abgefragt)."""
    due = jarvis_db.get_due_reminders()
    for r in due:
        jarvis_db.mark_notified(r["id"])
    return {"due": due}

# â”€â”€ I1: MODELL-DOWNLOAD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import subprocess as _sp

_pull_status: dict = {"running": False, "model": "", "progress": 0, "log": [], "done": False, "error": ""}

@app.post("/api/models/pull")
async def pull_model(request: Request):
    """I1: Startet Download eines Ollama-Modells im Hintergrund."""
    data  = await request.json()
    model = data.get("model", "").strip()
    if not model:
        return {"error": "Kein Modell angegeben"}
    if _pull_status["running"]:
        return {"error": f"Download laeuft bereits: {_pull_status['model']}"}

    _pull_status.update({"running": True, "model": model, "progress": 0,
                          "log": [f"Starte Download: {model}..."], "done": False, "error": ""})

    def _run_pull():
        import re
        try:
            proc = _sp.Popen(
                ["ollama", "pull", model],
                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                line = line.strip()
                if not line: continue
                _pull_status["log"].append(line)
                if len(_pull_status["log"]) > 50:
                    _pull_status["log"] = _pull_status["log"][-50:]
                m = re.search(r'(\d+)%', line)
                if m:
                    _pull_status["progress"] = int(m.group(1))
            proc.wait()
            if proc.returncode == 0:
                _pull_status.update({"progress": 100, "done": True,
                                      "log": _pull_status["log"] + [f"Fertig: {model}"]})
                log.info(f"[I1] Modell {model} erfolgreich heruntergeladen.")
            else:
                _pull_status.update({"error": f"Fehler beim Download (Code {proc.returncode})"})
        except FileNotFoundError:
            _pull_status.update({"error": "Ollama nicht gefunden â€” bitte installieren."})
        except Exception as e:
            _pull_status.update({"error": str(e)})
        finally:
            _pull_status["running"] = False

    threading.Thread(target=_run_pull, daemon=True).start()
    return {"ok": True, "model": model}


@app.get("/api/models/pull/status")
async def pull_status():
    """I1: Fortschritt des laufenden Downloads."""
    return dict(_pull_status)


@app.get("/api/models/list")
async def list_models():
    """I1: Alle installierten Modelle."""
    try:
        import requests as req
        r = req.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200:
            models = r.json().get("models", [])
            return {"models": [{"name": m["name"], "size": m.get("size", 0)} for m in models]}
    except Exception:
        pass
    return {"models": []}

# â”€â”€ A8: DEVELOP-MODUS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.post("/api/develop/propose")
async def develop_propose(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return {"error": "Kein Prompt"}
    if not jarvis_develop.is_develop_command(prompt) and not data.get("force"):
        return {"error": "Kein Develop-Befehl erkannt"}
    request_text = jarvis_develop.extract_develop_request(prompt)
    model = OLLAMA_STATE.get("code_model") or OLLAMA_STATE.get("best_model")
    if not model:
        return {"error": "Kein Modell verfuegbar"}
    try:
        import requests as req
        r = req.post("http://127.0.0.1:11434/api/generate", json={
            "model": model,
            "prompt": (
                "Du bist ein Python-Entwickler. Erstelle vollstaendigen, lauffaehigen Python-Code.\n"
                f"Aufgabe: {request_text}\n"
                "Antworte NUR mit dem Code, keine Erklaerung.\n"
                "Beginne direkt mit dem Code:\n"
            ),
            "stream": False, "options": {"temperature": 0.3, "num_predict": 1024},
        }, timeout=120)
        if r.status_code == 200:
            code = r.json().get("response", "").strip()
            target = data.get("file", "core/custom_feature.py")
            jarvis_develop.propose_code(target, code, request_text)
            return {"ok": True, "code": code, "file": target, "description": request_text}
        return {"error": f"Modell-Fehler: {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/develop/confirm")
async def develop_confirm():
    ok, msg = jarvis_develop.confirm_and_apply()
    return {"ok": ok, "message": msg}


@app.post("/api/develop/reject")
async def develop_reject():
    msg = jarvis_develop.reject()
    return {"ok": True, "message": msg}


@app.get("/api/develop/status")
async def develop_status():
    return jarvis_develop.get_state()


# â”€â”€ I7: GERAETE-ERKENNUNG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/api/devices")
async def get_devices():
    devices = []
    try:
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                devices.append({
                    "type": "disk", "name": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / 1e9, 1),
                    "free_gb":  round(usage.free  / 1e9, 1),
                })
            except Exception:
                pass
        net = psutil.net_if_stats()
        for name, stats in net.items():
            devices.append({
                "type": "network", "name": name,
                "speed_mb": stats.speed, "up": stats.isup,
            })
        mem = psutil.virtual_memory()
        devices.append({
            "type": "memory", "name": "RAM",
            "total_gb": round(mem.total / 1e9, 1),
            "available_gb": round(mem.available / 1e9, 1),
        })
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM"],
                capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.strip().split("\n")[1:]:
                if line.strip():
                    parts = line.strip().split()
                    devices.append({"type": "gpu", "name": " ".join(parts[:-1]) if len(parts) > 1 else line.strip()})
        except Exception:
            pass
    except Exception as e:
        log.warning(f"[Devices] Fehler: {e}")
    return {"devices": devices}


# â”€â”€ I6: PRIVATSPHAERE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import json as _json

_PRIVACY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "privacy.json")
_PRIVACY_DEFAULT = {
    "save_conversations": True,
    "save_tasks": True,
    "edge_tts_allowed": True,
    "security_log": True,
    "max_history_days": 30,
}

def _load_privacy() -> dict:
    try:
        with open(_PRIVACY_FILE, encoding="utf-8") as f:
            return {**_PRIVACY_DEFAULT, **_json.load(f)}
    except Exception:
        return dict(_PRIVACY_DEFAULT)

def _save_privacy(settings: dict):
    os.makedirs(os.path.dirname(_PRIVACY_FILE), exist_ok=True)
    with open(_PRIVACY_FILE, "w", encoding="utf-8") as f:
        _json.dump(settings, f, indent=2, ensure_ascii=False)

@app.get("/api/privacy")
async def get_privacy():
    return _load_privacy()

@app.post("/api/privacy")
async def set_privacy(request: Request):
    data     = await request.json()
    current  = _load_privacy()
    current.update({k: v for k, v in data.items() if k in _PRIVACY_DEFAULT})
    _save_privacy(current)
    return {"ok": True, "settings": current}






# â”€â”€ I2: UPDATE-PRUEFUNG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
JARVIS_VERSION = "8.0"

@app.get("/api/version")
async def get_version():
    """I2: Gibt aktuelle Version zurueck."""
    try:
        import urllib.request, json as _j
        url = "https://api.github.com/repos/felix-jarvis/jarvis-omni/releases/latest"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = _j.loads(r.read())
            latest = data.get("tag_name", "").lstrip("v")
            update = latest and latest != JARVIS_VERSION
            return {
                "current": JARVIS_VERSION,
                "latest":  latest,
                "update_available": update,
                "url": data.get("html_url", ""),
            }
    except Exception:
        return {
            "current": JARVIS_VERSION,
            "latest": None,
            "update_available": False,
            "note": "Kein Internet oder kein Update-Server.",
        }

# â”€â”€ F4: WELTNEUES / KRISEN-RADAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/api/worldnews")
async def get_worldnews():
    """F4: Aktuelle Welt-Nachrichten via RSS."""
    import urllib.request, xml.etree.ElementTree as ET
    feeds = [
        ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
        ("https://rss.dw.com/xml/rss-de-all",           "Deutsche Welle"),
    ]
    news = []
    for url, source in feeds:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                tree = ET.parse(r)
            for item in tree.findall(".//item")[:5]:
                title = item.findtext("title", "").strip()
                link  = item.findtext("link", "").strip()
                pub   = item.findtext("pubDate", "")[:16] if item.findtext("pubDate") else ""
                if title:
                    news.append({"title": title, "url": link,
                                 "source": source, "time": pub})
        except Exception as e:
            log.debug(f"[WorldNews] Feed-Fehler {source}: {e}")
    return {"news": news[:10], "count": len(news)}

# â”€â”€ A5: ALPHA-STATUS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@app.get("/api/alpha/status")
async def alpha_status():
    return jarvis_alpha.get_security_report()




@app.get("/api/health")
async def health_check():
    """H5: Doctor â€” prueft alle Systemkomponenten."""
    import shutil
    checks = {}

    # Python-Pakete
    for pkg in ["fastapi","uvicorn","psutil","requests","edge_tts","pyttsx3"]:
        try:
            __import__(pkg)
            checks[f"pkg_{pkg}"] = {"ok": True, "msg": "installiert"}
        except ImportError:
            checks[f"pkg_{pkg}"] = {"ok": False, "msg": f"FEHLT â€” pip install {pkg}"}

    # Ollama API
    try:
        import requests as req
        r = req.get("http://127.0.0.1:11434/api/tags", timeout=3)
        ok = r.status_code == 200
        models = [m["name"] for m in r.json().get("models", [])] if ok else []
        checks["ollama_api"]    = {"ok": ok,           "msg": f"Port 11434 {'offen' if ok else 'GESCHLOSSEN'}"}
        checks["ollama_models"] = {"ok": bool(models), "msg": models or ["KEIN MODELL â€” ollama pull llama3"]}
    except Exception as e:
        checks["ollama_api"]    = {"ok": False, "msg": f"Nicht erreichbar: {e}"}
        checks["ollama_models"] = {"ok": False, "msg": ["Ollama nicht gestartet"]}

    # Brain
    checks["einstein_warm"]  = {"ok": brain.is_ready(),                   "msg": "warm" if brain.is_ready() else "nicht warm"}
    checks["einstein_model"] = {"ok": bool(OLLAMA_STATE.get("best_model")), "msg": OLLAMA_STATE.get("best_model") or "kein Modell"}

    # System
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu  = psutil.cpu_percent(interval=0.5)
    checks["ram"]  = {"ok": mem.percent < 90,  "msg": f"{mem.percent:.0f}% ({mem.available//1024//1024} MB frei)"}
    checks["cpu"]  = {"ok": cpu < 95,           "msg": f"{cpu:.0f}% Last"}
    checks["disk"] = {"ok": disk.percent < 95,  "msg": f"{disk.percent:.0f}% voll ({disk.free//1024//1024//1024} GB frei)"}

    # Port + exe
    checks["port_8000"]  = {"ok": True, "msg": "offen (dieser Server antwortet)"}
    exe = OLLAMA_STATE.get("exe_path") or shutil.which("ollama")
    checks["ollama_exe"] = {"ok": bool(exe), "msg": exe or "NICHT GEFUNDEN â€” https://ollama.ai"}

    warnings = [k for k, v in checks.items() if not v["ok"]]
    all_ok   = not warnings
    return {
        "all_ok":   all_ok,
        "warnings": warnings,
        "checks":   checks,
        "summary":  "Alle Systeme nominal" if all_ok else f"{len(warnings)} Problem(e) gefunden",
    }




# â”€â”€ Static Frontend (muss NACH den Routen registriert werden) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount(
    "/",
    StaticFiles(directory=os.path.join(BASE_DIR, "frontend"), html=True),
    name="frontend",
)


# â”€â”€ Startup-Sequenz (lÃ¤uft in eigenem Thread, blockiert Server nicht) â”€â”€â”€â”€
def _port_free(port: int) -> bool:
    """Gibt True zurÃ¼ck wenn der Port frei ist."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) != 0


def _free_port(port: int):
    """Beendet NUR den Prozess, der genau diesen Port hÃ¤lt (A7-konform).

    Nutzt psutil.net_connections() - die STABILE API, die in ALLEN
    psutil-Versionen funktioniert (im Gegensatz zu
    process_iter(['connections']), das in neueren Versionen
    'invalid attr name connections' wirft)."""
    try:
        for conn in psutil.net_connections(kind='inet'):
            try:
                if conn.status == psutil.CONN_LISTEN and conn.laddr \
                   and conn.laddr.port == port and conn.pid and conn.pid > 0:
                    log.warning(f"[Port] Port {port} belegt von PID {conn.pid} â€” beende gezielt.")
                    try:
                        psutil.Process(conn.pid).kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    time.sleep(1)
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue
    except Exception as e:
        log.warning(f"[Port] Port-Check fehlgeschlagen: {e}")


def startup_sequence():
    """
    Phase 0: Port-Konflikt prÃ¼fen & sauber lÃ¶sen.
    Phase 1: Ollama finden & starten, auf HTTP-Port warten (bis 90s).
    Phase 2: Modell in VRAM laden / warmup (bis 180s).
    Phase 3: Browser automatisch Ã¶ffnen (G8).
    """
    log.info("â”" * 55)
    log.info(" JARVIS OMNI v7.6 â€” Startup-Sequenz")
    log.info("â”" * 55)

    # â”€â”€ Phase 0: Port-Check (nur Meldung - Cleanup macht der Hauptthread VOR uvicorn) â”€â”€
    # WICHTIG: Hier NICHT den Prozess beenden. Es laeuft parallel zu uvicorn.run()
    # und wuerde sonst den EIGENEN Server (der gerade Port 8000 bindet) beenden.
    log.info(f"[Phase 0] Port {PORT} wird vom Server genutzt - kein Cleanup im Thread.")

    # â”€â”€ Phase 1: Ollama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    log.info("[Phase 1/2] Omni-Scanner â€” suche und starte Ollama...")
    api_ready = omni_scanner()

    if not api_ready:
        log.warning("[Phase 1/2] âœ— Ollama nicht verfÃ¼gbar â€” Satelliten-Modus aktiv.")
        log.warning("[Phase 1/2] Tipp: 'ollama serve' im Terminal starten, dann Jarvis neu starten.")
    else:
        log.info(
            f"[Phase 1/2] âœ“ Ollama bereit Â· Modell: '{OLLAMA_STATE['best_model']}' Â· "
            f"Alle Modelle: {OLLAMA_STATE['available_models']}"
        )
        # â”€â”€ Phase 2: Warmup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        log.info("[Phase 2/2] Einstein Warmup â€” lade Modell in VRAM (bitte warten)...")
        brain.warmup()

        if brain.is_ready():
            log.info("â”" * 55)
            log.info(f" âœ“ EINSTEIN-CORE ONLINE Â· Modell: {OLLAMA_STATE['best_model']}")
            log.info(" Jarvis lÃ¤uft im VOLLEN Umfang.")
            log.info("â”" * 55)
        else:
            log.warning(" âœ— Warmup fehlgeschlagen â€” Satelliten-Modus.")
            log.warning(" PrÃ¼fe: ollama list")

    # â”€â”€ Phase 3: Browser Ã¶ffnen (G8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Warte kurz bis uvicorn wirklich hÃ¶rt
    for _ in range(20):
        time.sleep(0.5)
        if not _port_free(PORT):
            break  # Server lauscht
    url = f"http://127.0.0.1:{PORT}"
    log.info(f"[G8] Ã–ffne Browser: {url}")
    webbrowser.open(url)


if __name__ == "__main__":
    # â”€â”€ Port-Cleanup VOR dem Serverstart (im Hauptthread) â”€â”€
    # Jetzt ist der eigene Server noch NICHT gestartet, also gehoert
    # jeder Prozess auf Port 8000 einem ALTEN/anderen Jarvis - sicher beenden.
    if not _port_free(PORT):
        log.warning(f"[Start] Port {PORT} ist noch belegt - beende alten Jarvis...")
        _free_port(PORT)
        time.sleep(1.5)
        if not _port_free(PORT):
            log.error(f"[Start] Konnte Port {PORT} nicht freigeben - bitte schliesse das alte Jarvis-Fenster.")
            raise SystemExit("Port belegt")

    threading.Thread(target=startup_sequence, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="error")