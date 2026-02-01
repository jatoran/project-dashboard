"""Configuration service - loads/saves config.json with defaults."""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

CONFIG_FILE = Path(__file__).parent.parent / "data" / "config.json"

DEFAULT_LAUNCHERS = [
    {"id": "vscode", "name": "Code", "command": "__vscode__", "hotkey": "alt+c", "enabled": True, "builtin": True},
    {"id": "terminal", "name": "Terminal", "command": "__terminal__", "hotkey": "alt+t", "enabled": True, "builtin": True},
    {"id": "explorer", "name": "Folder", "command": "__explorer__", "hotkey": "alt+f", "enabled": True, "builtin": True},
    {"id": "claude", "name": "Claude", "command": "claude", "hotkey": "ctrl+c", "enabled": True, "builtin": False},
    {"id": "codex", "name": "Codex", "command": "codex", "hotkey": "ctrl+x", "enabled": True, "builtin": False},
    {"id": "opencode", "name": "OpenCode", "command": "opencode", "hotkey": "ctrl+z", "enabled": True, "builtin": False},
]


@dataclass
class Config:
    port: int = 37453
    global_hotkey: str = "win+shift+w"
    file_manager: Optional[str] = None
    launchers: List[Dict] = field(default_factory=lambda: [l.copy() for l in DEFAULT_LAUNCHERS])


class ConfigService:
    """Singleton service for managing application configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load config from file or create with defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                self.config = Config(
                    port=data.get("server", {}).get("port", 37453),
                    global_hotkey=data.get("global_hotkey", "win+shift+w"),
                    file_manager=data.get("file_manager"),
                    launchers=data.get("launchers", [l.copy() for l in DEFAULT_LAUNCHERS]),
                )
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Config load error, using defaults: {e}")
                self.config = Config()
                self._save()
        else:
            self.config = Config()
            self._save()

    def _save(self):
        """Save current config to file."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "server": {"port": self.config.port},
            "global_hotkey": self.config.global_hotkey,
            "file_manager": self.config.file_manager,
            "launchers": self.config.launchers,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_launchers(self, enabled_only: bool = True) -> List[Dict]:
        """Get launcher configurations."""
        if enabled_only:
            return [l for l in self.config.launchers if l.get("enabled", True)]
        return self.config.launchers

    def get_launcher_by_id(self, launcher_id: str) -> Optional[Dict]:
        """Get a specific launcher by ID."""
        for launcher in self.config.launchers:
            if launcher.get("id") == launcher_id:
                return launcher
        return None

    def update(self, **kwargs):
        """Update config values and save."""
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self._save()

    def reload(self):
        """Reload config from file."""
        self._load()


# Module-level convenience function
def get_config() -> ConfigService:
    """Get the singleton config service instance."""
    return ConfigService()
