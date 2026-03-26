"""Persistent CLI configuration stored at ~/.redteam/config.json"""
import json
import os
import stat
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".redteam"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class CLIConfig:
    api_url: str = "http://localhost:8000/api/v1"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    username: Optional[str] = None
    default_project_id: Optional[int] = None
    output_format: str = "table"  # table | json

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2))
        # Restrict permissions to owner-only on POSIX
        if sys.platform != "win32":
            CONFIG_FILE.chmod(0o600)

    @classmethod
    def load(cls) -> "CLIConfig":
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text())
            valid_keys = cls.__dataclass_fields__
            return cls(**{k: v for k, v in data.items() if k in valid_keys})
        except Exception:
            return cls()

    def clear_auth(self) -> None:
        self.access_token = None
        self.refresh_token = None
        self.username = None
        self.save()


def get_config() -> CLIConfig:
    return CLIConfig.load()
