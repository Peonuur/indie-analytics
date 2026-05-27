from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import redis.asyncio as aioredis

from app.config import get_settings
from app.database import engine, async_session
from app.models import Base, GameMetric
from app.schemas import MetricInput, MetricResponse

# === CORE SETUP ===
settings = get_settings()
active_connections: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True, encoding="utf-8")
    yield
    await app.state.redis.close()
    await engine.dispose()

app = FastAPI(title="Indie Analytics", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# === REST ENDPOINTS ===
@app.post("/api/v1/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def submit_metric(metric: MetricInput, db: AsyncSession = Depends(get_db)):
    cache_key = f"metric:latest:{metric.game_id}:{metric.player_id}"
    await app.state.redis.set(cache_key, metric.model_dump_json(), ex=3600)
    
    db_metric = GameMetric(**metric.model_dump())
    db.add(db_metric)
    try:
        await db.commit()
        await db.refresh(db_metric)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")
    
    broadcast_payload = {
        "id": db_metric.id,
        "game_id": db_metric.game_id,
        "player_id": db_metric.player_id,
        "event_type": db_metric.event_type,
        "payload": db_metric.payload,
        "created_at": db_metric.created_at.isoformat()
    }
    for ws in active_connections:
        try:
            await ws.send_json(broadcast_payload)
        except Exception:
            pass
    return db_metric

@app.get("/api/v1/metrics")
async def get_metrics(limit: int = 100, game_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(GameMetric).order_by(GameMetric.created_at.desc()).limit(limit)
    if game_id:
        query = query.where(GameMetric.game_id == game_id)
    result = await db.execute(query)
    return [
        {
            "id": m.id,
            "game_id": m.game_id,
            "player_id": m.player_id,
            "event_type": m.event_type,
            "payload": m.payload,
            "created_at": m.created_at.isoformat()
        }
        for m in result.scalars().all()
    ]

@app.get("/api/v1/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count()).select_from(GameMetric))
    players = await db.execute(select(func.count(func.distinct(GameMetric.player_id))))
    games = await db.execute(select(func.count(func.distinct(GameMetric.game_id))))
    types = await db.execute(
        select(GameMetric.event_type, func.count().label("count"))
        .group_by(GameMetric.event_type)
        .order_by(func.count().desc())
        .limit(5)
    )
    return {
        "total_events": total.scalar(),
        "unique_players": players.scalar(),
        "unique_games": games.scalar(),
        "top_events": [{"type": r.event_type, "count": r.count} for r in types.all()]
    }

@app.get("/health")
async def health_check():
    redis_status = "ok"
    try:
        await app.state.redis.ping()
    except Exception:
        redis_status = "error"
    return {"status": "alive", "db": "connected", "redis": redis_status}

# === WEBSOCKET REAL-TIME ===
@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# === ROUTING ===
@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
