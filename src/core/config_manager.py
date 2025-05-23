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
            },
            # Performance settings
            'performance': {
                'exiftool_pool_size': 3,
                'cache_enabled': True,
                'cache_size_mb': 100,
                'batch_size': 20,
                'max_concurrent_operations': 4
            }
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default = self._default_config()
                    return self._deep_merge(default, config)
            except (json.JSONDecodeError, IOError):
                return self._default_config()
        return self._default_config()

    def _deep_merge(self, default: Dict, override: Dict) -> Dict:
        """Deep merge override into default"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

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
        # Support nested keys with dot notation
        if '.' in key:
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value