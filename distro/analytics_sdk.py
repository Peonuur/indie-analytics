import json
import time
import threading
import urllib.request
import urllib.error
from collections import deque

class GameAnalytics:
    def __init__(self, config_path="game_config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.queue = deque()
        self.running = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def track(self, event_type: str, payload: dict = None):
        self.queue.append({
            "game_id": self.cfg["game_id"],
            "player_id": "session_" + str(int(time.time())),
            "event_type": event_type,
            "payload": payload or {}
        })

    def _worker(self):
        batch = []
        last_flush = time.time()
        while self.running:
            if self.queue:
                batch.append(self.queue.popleft())
            
            should_flush = (
                len(batch) >= self.cfg.get("batch_size", 10) or
                time.time() - last_flush >= self.cfg.get("flush_interval_sec", 5)
            )
            
            if should_flush and batch:
                self._send_batch(batch)
                batch.clear()
                last_flush = time.time()
            time.sleep(0.1)

    def _send_batch(self, items):
        data = json.dumps({"metrics": items}).encode("utf-8")
        req = urllib.request.Request(
            self.cfg["api_url"],
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass  # В продакшене: retry + локальный кэш

    def stop(self):
        self.running = False
