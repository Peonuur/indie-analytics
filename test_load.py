import asyncio
import aiohttp
import random

async def send_metric(session, i):
    payload = {
        "game_id": "indie_01",
        "player_id": f"player_{random.randint(1,100)}",
        "event_type": random.choice(["level_up", "death", "purchase", "achievement"]),
        "payload": {"score": random.randint(100, 9999)}
    }
    async with session.post("http://localhost:8000/api/v1/metrics", json=payload) as resp:
        return resp.status

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [send_metric(session, i) for i in range(500)]
        results = await asyncio.gather(*tasks)
        print(f"Отправлено: {len(results)}, Ошибок: {results.count(500)}")

if __name__ == "__main__":
    asyncio.run(main())
