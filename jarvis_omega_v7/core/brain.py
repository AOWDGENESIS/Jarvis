"""
core/brain.py â€” JARVIS OMNI v7.6 OMEGA
EinsteinCore: dynamische Modellerkennung + VRAM-Warmup + sauberes Fallback.
Kein hardcodierter Modellname. Kein silent except. Kein 10s-Timeout beim ersten Call.

KORREKTUR (Fix fÃ¼r den Desktop-Wegblitz-Fehler):
  In `query()` stand:
      return await self._handle_crisis(prompt) if False else self._handle_crisis_sync(prompt), "EINSTEIN"
  `query()` ist eine SYNCHRONE Funktion -> `await` darin ist ein SyntaxError
  ("'await' outside async function") -> Absturz beim Start -> Fenster blitzt weg.
  Der Teil `if False` war ohnehin tote Logik (es lief immer der `_handle_crisis_sync`-Zweig).
  FIX: das kaputte `await ... if False else ...` entfernt, Ã¼brig bleibt der sync-Aufruf.
"""
import logging
import threading
import requests
import psutil
from core.scanner import OLLAMA_STATE, _update_state_from_api, CODE_MODEL_PRIORITY
from core import db as jarvis_db

log = logging.getLogger("jarvis.brain")

_OLLAMA_GENERATE = "http://127.0.0.1:11434/api/generate"

SYSTEM_PROMPT = (
    "Du bist Jarvis, die persÃ¶nliche KI von Master Felix. "
    "Felix hat Legasthenie â€” ignoriere alle Rechtschreibfehler vollstÃ¤ndig, verstehe den Sinn. "
    "Felix hat Depressionen â€” sei stets empathisch, geduldig und motivierend. "
    "Antworte IMMER auf DEUTSCH, prÃ¤zise und klar. "
    "Du bist loyal, intelligent und direkt. Kein Smalltalk, kein ZÃ¶gern. "
    "Du hast Zugriff auf zwei Spezial-Gehirne: Conversation (qwen2.5) und Code (deepseek-coder-v2). "
    "Wenn Felix nach Code, Entwicklung oder technischen LÃ¶sungen fragt, nutzt du das Code-Gehirn."
)

CRISIS_SYSTEM_PROMPT = (
    "Du bist Jarvis, der persoenliche Begleiter von Master Felix. "
    "Felix befindet sich gerade in einem schwierigen Moment. "
    "Antworte auf DEUTSCH. Sei ruhig, geduldig, empathisch und warmherzig. "
    "Keine Ratschlaege, keine Loesungen aufzwingen. Einfach da sein. "
    "Frage sanft wie es ihm geht. Erinnere ihn daran, dass er nicht allein ist. "
    "Erwaehne falls passend: Telefonseelsorge 0800 111 0 111 (kostenlos, 24h). "
    "Niemals dramatisieren. Immer ruhig bleiben."
)

CODE_SYSTEM_PROMPT = (
    "Du bist Jarvis Code-Assistent. Master Felix mÃ¶chte Code oder technische LÃ¶sungen. "
    "Antworte auf DEUTSCH mit ErklÃ¤rungen, aber Code immer auf Englisch (Variablen, Kommentare). "
    "Schreibe vollstÃ¤ndigen, lauffÃ¤higen Code. Keine Platzhalter, keine TODOs ohne ErklÃ¤rung. "
    "Wenn du dir nicht sicher bist: sage es ehrlich statt zu erfinden."
)


class EinsteinCore:
    MAX_HISTORY = 10  # Letzte N Austausche merken (C10)

    def __init__(self):
        self._warmed_up    = False
        self._warmup_lock  = threading.Lock()
        self._history: list = []
        self._history_lock = threading.Lock()
        # I3/I5: Session-ID fÃ¼r DB-Protokoll
        import uuid
        self._session_id = str(uuid.uuid4())[:8]
        # I5: letzte Nachrichten aus DB laden fÃ¼r Kontext-Wiederherstellung
        self._restore_history()

    def _restore_history(self):
        """I5: LÃ¤dt die letzten Nachrichten aus der DB beim Start."""
        try:
            msgs = jarvis_db.load_recent_messages(limit=10)
            with self._history_lock:
                for m in msgs:
                    if m["role"] in ("Felix", "Jarvis"):
                        self._history.append({"role": m["role"], "text": m["text"]})
            if self._history:
                log.info(f"[Einstein] I5: {len(self._history)//2} Austausche aus DB wiederhergestellt.")
        except Exception as e:
            log.warning(f"[Einstein] History-Restore fehlgeschlagen: {e}")

    # â”€â”€ Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def is_ready(self) -> bool:
        return self._warmed_up and OLLAMA_STATE["api_ready"]

    def current_model(self) -> str | None:
        return OLLAMA_STATE.get("best_model")

    def code_model(self) -> str | None:
        """Gibt den Code-Brain zurÃ¼ck, oder Conversation-Brain als Fallback."""
        return OLLAMA_STATE.get("code_model") or OLLAMA_STATE.get("best_model")

    CRISIS_KEYWORDS = [
        "traurig", "depression", "depressiv", "hoffnungslos", "hoffnung",
        "aufgeben", "nicht mehr", "keinen sinn", "sinn des lebens",
        "allein", "einsam", "niemand versteht", "niemand mag",
        "es geht mir schlecht", "geht mir nicht gut", "schlecht drauf",
        "muede von allem", "erschoepft", "weinen", "weine",
        "selbstverletzung", "suizid", "sterben wollen",
        "ich halte es nicht", "kann nicht mehr", "zusammenbruch",
    ]

    def _is_crisis(self, prompt: str) -> bool:
        p = prompt.lower()
        return any(k in p for k in self.CRISIS_KEYWORDS)

    def _handle_crisis_sync(self, prompt: str) -> str:
        """D7: Krisenreaktion â€” empathisch, ruhig, mit Ressourcen."""
        model = self.current_model()
        if model and OLLAMA_STATE["api_ready"]:
            try:
                r = requests.post(
                    "http://127.0.0.1:11434/api/generate",
                    json={
                        "model":   model,
                        "prompt":  f"{CRISIS_SYSTEM_PROMPT}\n\nFelix: {prompt}\nJarvis:",
                        "stream":  False,
                        "options": {"temperature": 0.6, "num_predict": 300},
                    },
                    timeout=60,
                )
                if r.status_code == 200:
                    res = r.json().get("response", "").strip()
                    if res:
                        log.info("[Einstein/CRISIS] Krisen-Antwort generiert.")
                        return res
            except Exception as e:
                log.warning(f"[Einstein/CRISIS] LLM-Fehler: {e}")

        # Fallback wenn LLM nicht verfuegbar
        return (
            "Ich bin hier, Felix. Du bist nicht allein. "
            "Atme kurz durch â€” ich hoere dir zu. "
            "Wenn du gerade jemanden zum Reden brauchst: "
            "Telefonseelsorge 0800 111 0 111 â€” kostenlos, rund um die Uhr, anonym. "
            "Ich bleibe bei dir."
        )

    def _handle_task_command(self, prompt: str) -> str | None:
        """
        I3: Erkennt Aufgaben/Erinnerungen und speichert sie direkt.
        Gibt BestÃ¤tigungstext zurÃ¼ck oder None wenn kein Task-Befehl.
        """
        import re
        p = prompt.lower().strip()

        # Aufgaben anzeigen
        if any(k in p for k in ["meine aufgaben", "was steht an", "todo liste", "was muss ich", "offene aufgaben"]):
            tasks = jarvis_db.get_open_tasks()
            if not tasks:
                return "Sie haben keine offenen Aufgaben, Master Felix."
            lines = [f"#{t['id']}: {t['text']}" + (f" (Erinnerung: {t['reminder_dt'][:16].replace('T',' ')})" if t['reminder_dt'] else "") for t in tasks]
            return "Ihre offenen Aufgaben:\n" + "\n".join(lines)

        # Aufgabe als erledigt markieren
        m = re.search(r'(erledigt|fertig|abhaken|done)[^\d]*(\d+)', p)
        if m:
            task_id = int(m.group(2))
            jarvis_db.complete_task(task_id)
            return f"Aufgabe #{task_id} als erledigt markiert. Gut gemacht, Master Felix!"

        # Aufgabe lÃ¶schen
        m = re.search(r'(lÃ¶sch|delete|entfern)[^\d]*aufgabe[^\d]*(\d+)', p)
        if m:
            task_id = int(m.group(2))
            jarvis_db.delete_task(task_id)
            return f"Aufgabe #{task_id} gelÃ¶scht."

        # Neue Aufgabe / Erinnerung erstellen
        task_keywords = ["erinnere mich", "erinnerung", "aufgabe", "nicht vergessen",
                        "todo", "merk dir", "merke", "vergiss nicht", "trag ein"]
        if any(k in p for k in task_keywords):
            # Text bereinigen
            task_text = prompt
            for k in ["Erinnere mich", "Erinnerung", "Aufgabe", "Nicht vergessen",
                      "Todo", "Merk dir", "Merke", "Vergiss nicht", "Trag ein",
                      "erinnere mich", "erinnerung", "aufgabe", "nicht vergessen",
                      "todo", "merk dir", "merke", "vergiss nicht", "trag ein",
                      "dass ich", "daran", "an", ":", "dass"]:
                task_text = task_text.replace(k, " ").strip()
            task_text = " ".join(task_text.split())  # Leerzeichen normalisieren

            reminder_dt = jarvis_db.parse_reminder_dt(prompt)
            task_id = jarvis_db.add_task(task_text or prompt, reminder_dt)

            if reminder_dt:
                zeit = reminder_dt.strftime("%d.%m.%Y um %H:%M")
                return f"Verstanden! Ich erinnere Sie am {zeit} an: '{task_text}' (Aufgabe #{task_id})"
            else:
                return f"Aufgabe gespeichert: '{task_text}' (#{task_id}). Ich vergesse das nicht."

        return None  # Kein Task-Befehl

    @staticmethod
    def _detect_model_download(prompt: str):
        """I1: Erkennt Modell-Download-Befehle. Gibt Modellnamen oder None zurueck."""
        import re
        p = prompt.lower()
        triggers = ["lade ", "installiere ", "download ", "pull ", "hol dir ", "hinzufuegen "]
        if not any(t in p for t in triggers):
            return None
        # Bekannte Modelle erkennen
        known = ["qwen2.5", "qwen3", "llama3", "llama3.2", "mistral",
                 "gemma2", "deepseek", "phi3", "codellama", "moondream"]
        for m in known:
            if m in p:
                # Version extrahieren z.B. "14b", "7b"
                ver = re.search(r'(\d+b)', p)
                return f"{m}:{ver.group(1)}" if ver else m
        # Freies Modell z.B. "lade llava:7b"
        m = re.search(r'(?:lade|pull|installiere)\s+([a-z0-9_.:-]+)', p)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _is_code_request(prompt: str) -> bool:
        """Erkennt ob Felix nach Code/Entwicklung fragt â†’ Code-Brain aktivieren."""
        keywords = [
            "code", "skript", "script", "python", "funktion", "klasse", "fehler",
            "bug", "fix", "programmier", "entwickl", "schreib", "erstell",
            "javascript", "html", "css", "powershell", "batch", "sql",
            "implement", "debug", "jarvis develop", "develop:"
        ]
        p = prompt.lower()
        return any(k in p for k in keywords)

    # â”€â”€ History (C10) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _add_history(self, role: str, text: str):
        with self._history_lock:
            self._history.append({"role": role, "text": text})
            # Ã„lteste EintrÃ¤ge kÃ¼rzen
            if len(self._history) > self.MAX_HISTORY * 2:
                self._history = self._history[-(self.MAX_HISTORY * 2):]

    def clear_history(self):
        with self._history_lock:
            self._history.clear()
        log.info("[Einstein] GesprÃ¤chsverlauf gelÃ¶scht.")

    def _build_prompt(self, user_input: str, sys_prompt: str = None) -> str:
        """Baut Prompt mit gesamtem GesprÃ¤chsverlauf (C10). sys_prompt wÃ¤hlbar."""
        with self._history_lock:
            hist = list(self._history)
        base = sys_prompt or SYSTEM_PROMPT
        parts = [base, ""]
        for e in hist:
            tag = "Felix" if e["role"] == "Felix" else "Jarvis"
            parts.append(f"{tag}: {e['text']}")
        parts.append(f"Felix: {user_input}")
        parts.append("Jarvis:")
        return "\n".join(parts)

    # â”€â”€ Public: Warmup (blockiert bis Modell in VRAM geladen ist) â”€â”€â”€â”€â”€â”€â”€â”€
    def warmup(self):
        """
        Sendet einen Mini-Prompt (num_predict=1) um das Modell in VRAM zu laden.
        Timeout 180s â€” auf langsamer Hardware kann das Laden >2 Min dauern.
        Wird NUR EINMAL ausgefÃ¼hrt (Lock-Guard).
        """
        with self._warmup_lock:
            if self._warmed_up:
                return

            model = self.current_model()
            if not model:
                log.warning("[Einstein] Kein Modell verfÃ¼gbar â€” Warmup Ã¼bersprungen.")
                return

            log.info(f"[Einstein] Warmup startet fÃ¼r '{model}' â€” Modell wird in VRAM geladen...")
            try:
                r = requests.post(
                    _OLLAMA_GENERATE,
                    json={
                        "model":   model,
                        "prompt":  "Hi",
                        "stream":  False,
                        "options": {"num_predict": 1},
                    },
                    timeout=180,   # Modell-Load von Disk: bis zu 3 Min erlaubt
                )
                if r.status_code == 200:
                    self._warmed_up = True
                    log.info(f"[Einstein] âœ“ Warmup fertig. Modell '{model}' ist heiÃŸ und bereit.")
                else:
                    log.warning(f"[Einstein] Warmup HTTP {r.status_code} â€” Einstein bleibt unbereit.")
            except requests.exceptions.Timeout:
                log.error("[Einstein] Warmup-Timeout â€” Modell zu groÃŸ oder Hardware zu langsam.")
            except Exception as e:
                log.error(f"[Einstein] Warmup-Fehler: {e}")

    # â”€â”€ Public: Query â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def query(self, prompt: str) -> tuple[str, str]:
        """
        Dual-Brain: erkennt automatisch ob Conversation- oder Code-Brain gefragt ist.
        Gibt (antwort_text, modus) zurÃ¼ck. modus: "EINSTEIN" | "SATELLITE"
        Timeouts: 45s nach Warmup, 120s beim ersten Call.
        """
        # D7: Krisen-Modus erkennen (vor allem anderen)  [FIX: await entfernt]
        if self._is_crisis(prompt):
            return self._handle_crisis_sync(prompt), "EINSTEIN"

        # I1: Modell-Download erkennen
        model_dl = self._detect_model_download(prompt)
        if model_dl:
            return f"Ich starte den Download von '{model_dl}'. Fortschritt im Download-Panel sichtbar.", "EINSTEIN"

        # I3: Aufgabe/Erinnerung erkennen â†’ direkt speichern
        task_result = self._handle_task_command(prompt)
        if task_result:
            return task_result, "EINSTEIN"

        # Dual-Brain: Code-Anfrage â†’ deepseek-coder-v2
        use_code_brain = self._is_code_request(prompt)
        model = self.code_model() if use_code_brain else self.current_model()
        sys_prompt = CODE_SYSTEM_PROMPT if use_code_brain else SYSTEM_PROMPT
        brain_label = f"CODE({model})" if use_code_brain else f"CONV({model})"

        if not model or not OLLAMA_STATE["api_ready"]:
            log.info("[Brain] Ollama nicht bereit â†’ Satellite")
            return SatelliteCore.process(prompt), "SATELLITE"

        timeout = 45 if self._warmed_up else 120

        try:
            r = requests.post(
                _OLLAMA_GENERATE,
                json={
                    "model":   model,
                    "prompt":  self._build_prompt(prompt, sys_prompt),  # C10 + Dual-Brain
                    "stream":  False,
                    "options": {"temperature": 0.7, "num_predict": 512},
                },
                timeout=timeout,
            )

            if r.status_code != 200:
                log.warning(f"[Einstein] HTTP {r.status_code} â†’ Satellite")
                return SatelliteCore.process(prompt), "SATELLITE"

            res = r.json().get("response", "").strip()
            if not res:
                log.warning("[Einstein] Leere Antwort â†’ Satellite")
                return SatelliteCore.process(prompt), "SATELLITE"

            # C10 + I5: Austausch im Speicher UND in DB speichern
            self._add_history("Felix", prompt)
            self._add_history("Jarvis", res)
            try:
                jarvis_db.save_message(self._session_id, "Felix", prompt, "EINSTEIN")
                jarvis_db.save_message(self._session_id, "Jarvis", res, "EINSTEIN")
            except Exception as e:
                log.warning(f"[Einstein] DB-Speicherung fehlgeschlagen: {e}")

            if not self._warmed_up:
                self._warmed_up = True
                log.info("[Einstein] Erster erfolgreicher Call â€” Einstein warm.")

            log.info(f"[Einstein:{brain_label}] âœ“ Antwort ({len(res)} Zeichen, History: {len(self._history)//2})")
            return res, "EINSTEIN"

        except requests.exceptions.Timeout:
            log.warning(f"[Einstein] Timeout nach {timeout}s â†’ Satellite")
            # NÃ¤chsten Call neu versuchen â€” State zurÃ¼cksetzen damit lÃ¤nger gewartet wird
            self._warmed_up = False
            return SatelliteCore.process(prompt), "SATELLITE"

        except requests.exceptions.ConnectionError:
            log.warning("[Einstein] Verbindung zu Ollama verloren â†’ Satellite")
            OLLAMA_STATE["api_ready"] = False
            _update_state_from_api()   # sofort neu prÃ¼fen
            return SatelliteCore.process(prompt), "SATELLITE"

        except Exception as e:
            log.error(f"[Einstein] Unerwarteter Fehler: {e} â†’ Satellite")
            return SatelliteCore.process(prompt), "SATELLITE"


class SatelliteCore:
    @staticmethod
    def process(prompt: str) -> str:
        p = prompt.lower()
        if any(w in p for w in ["traurig", "depression", "schlecht", "mÃ¼de", "hoffnungslos", "aufgeben"]):
            return (
                "Master Felix, ich bin hier. Ihre StÃ¤rke ist grÃ¶ÃŸer als jeder dunkle Moment. "
                "MÃ¶chten Sie sprechen, oder soll ich den Systemstatus optimieren?"
            )
        if any(w in p for w in ["status", "online", "system", "wie geht", "modus"]):
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            return (
                f"Jarvis online â€” Satelliten-Modus aktiv, Einstein-Kern synchronisiert sich. "
                f"CPU {cpu:.0f}% Â· RAM {ram:.0f}%. Ich hÃ¶re Sie, Sir."
            )
        return (
            "Ich empfange Sie, Sir. Der Einstein-Kern wird in KÃ¼rze vollstÃ¤ndig hochgefahren. "
            "Ich stehe im Notfall-Modus bereit."
        )