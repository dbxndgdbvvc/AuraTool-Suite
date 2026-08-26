"""
AuraTool-Suite — Configuration Manager
========================================
Centralized configuration with YAML/JSON file support and environment variable overrides.

Features:
- Load from config.yaml, config.json, or environment variables
- Sensible defaults for all settings
- Type-safe access with validation
- Hot-reload support for runtime changes
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("AuraTool.Config")

# Default configuration values
DEFAULTS = {
    # Server settings
    "server": {
        "host": "0.0.0.0",
        "port": 8500,
        "tls_port": 8600,
        "auto_ssl": False,
        "cors_origins": ["*"],
    },

    # License settings
    "license": {
        "server_url": "https://license.auratool.com:8600",
        "timeout": 10,
        "data_dir": "~/.auratool",
    },

    # Download settings
    "download": {
        "directory": "./downloads",
        "max_retries": 3,
        "chunk_size": 65536,
        "connect_timeout": 30,
    },

    # API settings
    "api": {
        "rate_limit": 100,  # requests per minute
        "max_body_size": 10485760,  # 10MB
        "require_auth": True,
        "key_rotation_days": 90,
    },

    # Logging settings
    "logging": {
        "level": "INFO",
        "file": None,  # None = stdout only
        "max_size_mb": 10,
        "backup_count": 5,
    },

    # Localization settings
    "localization": {
        "default_lang": "en",
        "rtl_languages": ["ar", "fa", "ur"],
    },

    # Factory settings
    "factory": {
        "data_dir": "./factory_data",
        "auto_backup": True,
        "backup_interval_hours": 24,
    },

    # Device settings
    "devices": {
        "adb_path": "adb",
        "fastboot_path": "fastboot",
        "scan_interval": 5,  # seconds
    },
}


class Config:
    """
    Centralized configuration manager with file and environment variable support.
    
    Usage:
        config = Config()
        port = config.get("server.port")
        host = config.get("server.host", "localhost")
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config file (YAML or JSON). If None, searches:
                        1. ./config.yaml
                        2. ./config.json
                        3. ~/.auratool/config.yaml
                        4. ~/.auratool/config.json
        """
        self._config = {}
        self._config_path = None
        
        # Load defaults
        self._config = self._deep_copy(DEFAULTS)
        
        # Find and load config file
        if config_path:
            self._load_file(config_path)
        else:
            self._find_and_load_config()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        logger.info(f"Configuration loaded from {self._config_path or 'defaults'}")

    def _deep_copy(self, d: dict) -> dict:
        """Deep copy a dictionary."""
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = self._deep_copy(v)
            else:
                result[k] = v
        return result

    def _find_and_load_config(self) -> None:
        """Search for config file in standard locations."""
        search_paths = [
            Path("./config.yaml"),
            Path("./config.json"),
            Path.home() / ".auratool" / "config.yaml",
            Path.home() / ".auratool" / "config.json",
        ]
        
        for path in search_paths:
            if path.exists():
                self._load_file(str(path))
                return

    def _load_file(self, path: str) -> None:
        """Load configuration from a file."""
        path = Path(path).expanduser()
        
        if not path.exists():
            logger.warning(f"Config file not found: {path}")
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if path.suffix in (".yaml", ".yml"):
                try:
                    import yaml
                    file_config = yaml.safe_load(content)
                except ImportError:
                    logger.warning("PyYAML not installed, trying JSON fallback")
                    file_config = json.loads(content)
            else:
                file_config = json.loads(content)
            
            if file_config:
                self._config = self._merge_dicts(self._config, file_config)
                self._config_path = str(path)
                logger.info(f"Loaded config from {path}")
        
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load config from {path}: {e}")

    def _merge_dicts(self, base: dict, override: dict) -> dict:
        """Deep merge override into base dict."""
        result = self._deep_copy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides.
        
        Environment variables follow the pattern: AURATOOL_SECTION_KEY=value
        Examples:
            AURATOOL_SERVER_PORT=9000
            AURATOOL_LICENSE_TIMEOUT=15
            AURATOOL_API_REQUIRE_AUTH=false
        
        Special mappings for multi-word keys:
            AURATOOL_API_REQUIRE_AUTH -> api.require_auth
            AURATOOL_DOWNLOAD_MAX_RETRIES -> download.max_retries
        """
        prefix = "AURATOOL_"
        
        # Explicit mapping for env vars with multi-word keys
        env_to_config = {
            "AURATOOL_SERVER_PORT": "server.port",
            "AURATOOL_SERVER_HOST": "server.host",
            "AURATOOL_SERVER_TLS_PORT": "server.tls_port",
            "AURATOOL_SERVER_AUTO_SSL": "server.auto_ssl",
            "AURATOOL_LICENSE_SERVER_URL": "license.server_url",
            "AURATOOL_LICENSE_TIMEOUT": "license.timeout",
            "AURATOOL_LICENSE_DATA_DIR": "license.data_dir",
            "AURATOOL_DOWNLOAD_DIRECTORY": "download.directory",
            "AURATOOL_DOWNLOAD_MAX_RETRIES": "download.max_retries",
            "AURATOOL_DOWNLOAD_CHUNK_SIZE": "download.chunk_size",
            "AURATOOL_DOWNLOAD_CONNECT_TIMEOUT": "download.connect_timeout",
            "AURATOOL_API_RATE_LIMIT": "api.rate_limit",
            "AURATOOL_API_MAX_BODY_SIZE": "api.max_body_size",
            "AURATOOL_API_REQUIRE_AUTH": "api.require_auth",
            "AURATOOL_API_KEY_ROTATION_DAYS": "api.key_rotation_days",
            "AURATOOL_LOGGING_LEVEL": "logging.level",
            "AURATOOL_LOGGING_FILE": "logging.file",
            "AURATOOL_LOGGING_MAX_SIZE_MB": "logging.max_size_mb",
            "AURATOOL_LOGGING_BACKUP_COUNT": "logging.backup_count",
            "AURATOOL_LOCALIZATION_DEFAULT_LANG": "localization.default_lang",
            "AURATOOL_FACTORY_DATA_DIR": "factory.data_dir",
            "AURATOOL_FACTORY_AUTO_BACKUP": "factory.auto_backup",
            "AURATOOL_FACTORY_BACKUP_INTERVAL_HOURS": "factory.backup_interval_hours",
            "AURATOOL_DEVICES_ADB_PATH": "devices.adb_path",
            "AURATOOL_DEVICES_FASTBOOT_PATH": "devices.fastboot_path",
            "AURATOOL_DEVICES_SCAN_INTERVAL": "devices.scan_interval",
        }
        
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue
            
            # Use explicit mapping if available
            if env_key in env_to_config:
                config_path = env_to_config[env_key]
                self.set(config_path, self._parse_env_value(env_value))
            else:
                # Fallback: try to parse generic pattern
                key_path = env_key[len(prefix):].lower()
                parts = key_path.split("_")
                
                if len(parts) >= 2:
                    section = parts[0]
                    if section in self._config and isinstance(self._config[section], dict):
                        # Try to find the key in the section
                        for config_key in self._config[section].keys():
                            if config_key == "_".join(parts[1:]):
                                self._config[section][config_key] = self._parse_env_value(env_value)
                                break

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate Python type."""
        # Boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]
        
        # String
        return value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., "server.port")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split(".")
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., "server.port")
            value: Value to set
        """
        keys = key_path.split(".")
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        logger.debug(f"Config set: {key_path} = {value}")

    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to a file.
        
        Args:
            path: File path. If None, saves to original path or ./config.json
        """
        save_path = Path(path or self._config_path or "./config.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            self._config_path = str(save_path)
            logger.info(f"Configuration saved to {save_path}")
        
        except OSError as e:
            logger.error(f"Failed to save config to {save_path}: {e}")

    def get_section(self, section: str) -> dict:
        """Get an entire configuration section."""
        return self._deep_copy(self._config.get(section, {}))

    def get_all(self) -> dict:
        """Get the entire configuration dictionary."""
        return self._deep_copy(self._config)

    def validate(self) -> list:
        """
        Validate configuration values.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Server validation
        port = self.get("server.port")
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append(f"Invalid server.port: {port} (must be 1-65535)")
        
        # Download validation
        retries = self.get("download.max_retries")
        if not isinstance(retries, int) or retries < 0:
            errors.append(f"Invalid download.max_retries: {retries} (must be >= 0)")
        
        # API validation
        rate_limit = self.get("api.rate_limit")
        if not isinstance(rate_limit, int) or rate_limit < 0:
            errors.append(f"Invalid api.rate_limit: {rate_limit} (must be >= 0)")
        
        return errors

    def __repr__(self) -> str:
        return f"Config(path={self._config_path}, keys={list(self._config.keys())})"


# Singleton instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reset_config() -> None:
    """Reset the global configuration instance (for testing)."""
    global _config
    _config = None
