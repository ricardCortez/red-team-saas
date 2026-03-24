"""RiskScore model - computed risk scoring per task"""
from sqlalchemy import Column, Integer, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class RiskScore(Base, BaseModel):
    """Risk score associated with a task execution"""

    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    score = Column(Numeric(4, 2), nullable=False)   # 0.0 – 10.0
    components = Column(Text, nullable=True)         # JSON breakdown of score factors
    justification = Column(Text, nullable=True)

    task = relationship("Task")

    @property
    def risk_level(self) -> str:
        """Derive risk level from numeric score"""
        try:
            s = float(self.score)
        except (TypeError, ValueError):
            return "UNKNOWN"
        if s >= 9.0:
            return "CRITICAL"
        if s >= 7.0:
            return "HIGH"
        if s >= 4.0:
            return "MEDIUM"
        if s >= 1.0:
            return "LOW"
        return "INFO"

    def __repr__(self):
        return f"<RiskScore(id={self.id}, task_id={self.task_id}, score={self.score}, level={self.risk_level})>"
