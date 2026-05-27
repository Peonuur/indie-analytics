import os
import sys
import time
import json
import re
import requests
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collections import deque
from typing import List, Dict, Any

class MetricHarvester(FileSystemEventHandler):
    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
        
        self.api_url = self.cfg.get("api_url", "http://localhost:8000")
        self.watch_dir = Path(self.cfg["watch_dir"])
        self.game_id = self.cfg.get("game_id", "unknown")
        self.player_id = self.cfg.get("player_id", "harvested_session")
        
        self.processed_files = set()
        self.metric_queue: deque = deque()
        self.batch_size = self.cfg.get("batch_size", 20)
        self.flush_interval = self.cfg.get("flush_interval_sec", 5)
        self.running = True
        
        # Компилируем паттерны парсинга
        self.parsers = []
        for p in self.cfg.get("parsers", []):
            self.parsers.append({
                "type": p["type"],
                "pattern": re.compile(p["pattern"]),
                "extract": p.get("extract", {})
            })
        
        # Запускаем фоновый отправщик
        self.sender_thread = threading.Thread(target=self._batch_sender, daemon=True)
        self.sender_thread.start()

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_process(event.src_path)

    def on_modified(self, event):
        # Некоторые игры дописывают в лог. Обрабатываем с задержкой
        if not event.is_directory:
            self._schedule_process(event.src_path, delay=2.0)

    def _schedule_process(self, file_path: str, delay: float = 0.5):
        def delayed_process():
            time.sleep(delay)
            self._process_file(file_path)
        threading.Thread(target=delayed_process, daemon=True).start()

    def _process_file(self, file_path: str):
        if file_path in self.processed_files:
            return
        
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return

        # Ждём, пока игра отпустит файл (снимаем файловую блокировку)
        if not self._wait_for_unlock(path, timeout=5.0):
            return

        try:
            metrics = self._parse_file(path)
            for m in metrics:
                m.setdefault("game_id", self.game_id)
                m.setdefault("player_id", self.player_id)
                m.setdefault("payload", {})
                self.metric_queue.append(m)
            
            self.processed_files.add(file_path)
            print(f"[Harvester] ✅ Processed: {path.name} ({len(metrics)} metrics)")
        except Exception as e:
            print(f"[Harvester] ❌ Parse error {path.name}: {e}")

    def _wait_for_unlock(self, path: Path, timeout: float) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Пробуем открыть эксклюзивно. Если игра держит файл → PermissionError
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    f.read(1)  # Читаем байт, чтобы убедиться, что поток не заблокирован
                return True
            except (PermissionError, IOError):
                time.sleep(0.3)
            except Exception:
                return False
        return False

    def _parse_file(self, path: Path) -> List[Dict[str, Any]]:
        metrics = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 1. JSON Lines (самый частый формат в современных играх)
                    if line.startswith("{"):
                        try:
                            data = json.loads(line)
                            if "event_type" in data:
                                metrics.append(data)
                                continue
                        except json.JSONDecodeError:
                            pass
                    
                    # 2. Пользовательские regex-паттерны из конфига
                    for parser in self.parsers:
                        match = parser["pattern"].search(line)
                        if match:
                            payload = {}
                            for key, group_idx in parser["extract"].items():
                                payload[key] = match.group(group_idx)
                            metrics.append({
                                "event_type": self.cfg.get("default_event", "log_entry"),
                                "payload": payload
                            })
                            break
        except Exception as e:
            print(f"[Harvester] Read error: {e}")
        return metrics

    def _batch_sender(self):
        last_flush = time.time()
        while self.running:
            should_flush = (
                len(self.metric_queue) >= self.batch_size or
                time.time() - last_flush >= self.flush_interval
            )
            
            if should_flush and self.metric_queue:
                batch = [self.metric_queue.popleft() for _ in range(len(self.metric_queue))]
                self._send_batch(batch)
                last_flush = time.time()
            
            time.sleep(0.2)

    def _send_batch(self, batch: List[Dict]):
        url = f"{self.api_url}/api/v1/metrics"
        headers = {"Content-Type": "application/json"}
        try:
            # Отправляем по одному (FastAPI принимает одиночные POST)
            # Для продакшена лучше добавить эндпоинт /api/v1/metrics/batch
            for metric in batch:
                requests.post(url, json=metric, headers=headers, timeout=2)
            print(f"[Harvester] 📤 Sent {len(batch)} metrics")
        except Exception as e:
            print(f"[Harvester] 📡 API error: {e}")

    def stop(self):
        self.running = False
        self.sender_thread.join(timeout=3)

def main():
    if len(sys.argv) < 2:
        print("Usage: python harvester.py <config.json>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        sys.exit(1)

    harvester = MetricHarvester(config_path)
    observer = Observer()
    observer.schedule(harvester, str(harvester.watch_dir), recursive=True)
    observer.start()
    
    print(f"[Harvester] ️ Watching: {harvester.watch_dir}")
    print("[Harvester] Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Harvester] 🛑 Stopping...")
        harvester.stop()
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
