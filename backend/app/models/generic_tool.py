"""Generic Tool Model for dynamic tool execution"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import BaseModel
import enum


class ExecutionModeEnum(str, enum.Enum):
    core_direct = "core_direct"
    generic_cli = "generic_cli"
    plugin = "plugin"
    api_gateway = "api_gateway"


class ToolCategoryEnum(str, enum.Enum):
    osint = "osint"
    enumeration = "enumeration"
    brute_force = "brute_force"
    phishing = "phishing"
    exploitation = "exploitation"
    post_exploitation = "post_exploitation"
    cryptography = "cryptography"
    network = "network"
    malware = "malware"
    custom = "custom"


class GenericToolConfig(Base, BaseModel):
    """Configuration for generic/dynamic tool execution"""

    __tablename__ = "generic_tool_configs"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(SQLEnum(ToolCategoryEnum), nullable=False, index=True)
    execution_mode = Column(SQLEnum(ExecutionModeEnum), default=ExecutionModeEnum.generic_cli)
    command_template = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    docker_image = Column(String(255), nullable=True)   # Para ejecutar en Docker
    requires_auth = Column(String(50), nullable=True)   # api_key, username_password, etc
    output_format = Column(String(50), default="json")  # json, xml, csv, text
    parser_function = Column(String(255), nullable=True)  # Nombre de función parser
    is_enabled = Column(String(1), default="Y")

    executions = relationship("ToolExecution", back_populates="tool_config", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GenericToolConfig(name={self.tool_name}, mode={self.execution_mode})>"


class ToolExecution(Base, BaseModel):
    """Execution history of generic tools"""

    __tablename__ = "tool_executions"

    id = Column(Integer, primary_key=True, index=True)
    tool_config_id = Column(Integer, ForeignKey("generic_tool_configs.id"), nullable=False, index=True)
    command_executed = Column(String(2000), nullable=False)
    target = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    output = Column(Text, nullable=True)
    parsed_output = Column(Text, nullable=True)  # JSON parsed
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    tool_config = relationship("GenericToolConfig", back_populates="executions")

    def __repr__(self):
        return f"<ToolExecution(tool={self.tool_config_id}, status={self.status})>"
