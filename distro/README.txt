 Indie Analytics - Быстрый старт

1. Убедись, что установлен Docker Desktop:
   https://www.docker.com/products/docker-desktop

2. Запусти файл:
   • Linux: ./AnalyticsLauncher
   • Windows: AnalyticsLauncher.exe

3. Откроется браузер с дашбордом. Не закрывай консоль/окно лаунчера.

4. Для интеграции с игрой:
   • Скопируй game_config.json в папку с игрой
   • Измени game_id на название твоей игры
   • Добавь analytics_sdk.py в проект игры
   • Вызывай analytics.track("событие", {"данные": 123})

5. Остановка:
   • Закрой окно лаунчера (Ctrl+C)
   • Или выполни: docker compose down

⚠️ Важно: 
• Не меняй .env файл без необходимости
• API работает только на localhost
• Для сетевого доступа нужен проброс портов или ngrok
