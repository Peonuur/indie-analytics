import os
import sys
import time
import subprocess
import webbrowser
import urllib.request
import urllib.error
import json
import platform

# Пути
COMPOSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker-compose.yml")
API_URL = "http://localhost:8000/health"
DASHBOARD_URL = "http://localhost:8000"

def log(msg):
    print(f"[Launcher] {msg}")

def check_docker():
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except Exception:
        return False

def wait_for_api(timeout=30):
    log("Ожидание запуска API...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(API_URL, timeout=2)
            if req.status == 200:
                data = json.loads(req.read())
                if data.get("status") == "alive":
                    log("API готов!")
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False

def start_services():
    if not check_docker():
        log("❌ Docker не установлен. Установи Docker Desktop: https://www.docker.com/products/docker-desktop")
        sys.exit(1)

    log("Запуск контейнеров...")
    try:
        subprocess.run(["docker", "compose", "up", "-d", "--build"], check=True)
    except Exception as e:
        log(f" Ошибка запуска Docker: {e}")
        sys.exit(1)

    if not wait_for_api():
        log("❌ API не ответил вовремя. Проверь логи: docker compose logs app")
        sys.exit(1)

    log(f"✅ Открываю дашборд: {DASHBOARD_URL}")
    webbrowser.open(DASHBOARD_URL)
    log(" Лаунчер работает. Закрой это окно, чтобы остановить сервисы.")
    log("💡 Для остановки вручную: docker compose down")

    log("Запуск харвестера метрик...")
    harvester_proc = subprocess.Popen(
        [sys.executable, "harvester.py", "harvester_config.json"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    # Держим процесс живым (чтобы пользователь видел статус)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("⏹ Остановка...")
        subprocess.run(["docker", "compose", "down"])

if __name__ == "__main__":
    start_services()
