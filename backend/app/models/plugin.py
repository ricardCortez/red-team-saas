"""Plugin Model for community plugins (OPCIÓN B only)"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel


class Plugin(Base, BaseModel):
    """Community plugin for extending functionality"""

    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    version = Column(String(20), default="1.0.0")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)  # osint, exploitation, etc

    # Plugin metadata
    source_url = Column(String(500), nullable=True)   # GitHub, etc
    documentation = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)  # Python dependencies

    # Ratings
    download_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)  # 0-5 stars

    # Marketplace (OPCIÓN B)
    is_public = Column(String(1), default="N")  # Y/N
    is_paid = Column(String(1), default="N")
    price = Column(Float, nullable=True)          # USD
    revenue_share = Column(Float, default=0.3)   # 30% to creator

    # Status
    status = Column(String(20), default="draft")  # draft, pending_review, published, suspended

    author = relationship("User")
    executions = relationship("PluginExecution", back_populates="plugin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plugin(name={self.name}, version={self.version})>"


class PluginExecution(Base, BaseModel):
    """Execution history of community plugins"""

    __tablename__ = "plugin_executions"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False, index=True)
    target = Column(String(255), nullable=True)
    parameters = Column(Text, nullable=True)  # JSON
    status = Column(String(20), default="running")
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    plugin = relationship("Plugin", back_populates="executions")

    def __repr__(self):
        return f"<PluginExecution(plugin_id={self.plugin_id}, status={self.status})>"
