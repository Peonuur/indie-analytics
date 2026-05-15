from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class GameMetric(Base):
    __tablename__ = "metrics"  # ← Два подчёркивания
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    game_id = Column(String, index=True, nullable=False)
    player_id = Column(String, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
