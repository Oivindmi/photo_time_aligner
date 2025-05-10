import json
import os
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manages application configuration and preferences"""

    def __init__(self):
        self.config_dir = Path(os.environ['APPDATA']) / 'PhotoTimeAligner'
        self.config_file = self.config_dir / 'config.json'
        self.config = self._load_config()

    def _default_config(self) -> Dict[str, Any]:
        """Returns default configuration"""
        return {
            'last_master_folder': '',
            'move_to_master': True,
            'window_geometry': {
                'x': 100,
                'y': 100,
                'width': 900,
                'height': 700
            }
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If config is corrupted, return defaults
                return self._default_config()
        return self._default_config()

    def save(self):
        """Save current configuration to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value