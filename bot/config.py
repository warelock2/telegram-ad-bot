"""
Configuration loader

This module loads all configuration from environment variables,
validates them, and exposes them as a singleton 'settings' object.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file, if it exists.
load_dotenv()

class SettingsError(Exception):
    """Custom exception for configuration errors."""
    pass

class Settings:
    """
    A singleton class to hold all application settings.
    It reads settings from environment variables and performs necessary
    type conversions and validation.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
        # --- Core Credentials ---
        self.bot_token: str = self._get_env("BOT_TOKEN", required=True)
        self.telegram_chat_id: str = self._get_env("TELEGRAM_CHAT_ID", required=True)

        # --- Content ---
        self.ads_directory: str = self._get_env("ADS_DIRECTORY", default="ads")
        self.auth_text: str = self._get_env("AUTH_TEXT", default="")

        # --- Scheduling ---
        self.time_based_frequency_hours: float = self._get_env_float("TIME_BASED_FREQUENCY_HOURS", 12.0)
        self.randomization_jitter_minutes: int = self._get_env_int("RANDOMIZATION_JITTER_MINUTES", 30)
        self.post_success_cooldown_minutes: float = self._get_env_float("POST_SUCCESS_COOLDOWN_MINUTES", 30.0)
        
        # --- Activity Check ---
        self.activity_check_enabled: bool = self._get_env_bool("ACTIVITY_CHECK_ENABLED", True)
        self.activity_check_messages: int = self._get_env_int("ACTIVITY_CHECK_MESSAGES", 10)
        self.activity_check_tframe_mins: int = self._get_env_int("ACTIVITY_CHECK_TIMEFRAME_MINUTES", 60)
        self.activity_check_retry_delay_mins: float = self._get_env_float("ACTIVITY_CHECK_RETRY_DELAY_MINUTES", 30.0)

        # --- Operational ---
        self.log_level: str = self._get_env("LOG_LEVEL", "INFO").upper()
        self.dry_run: bool = self._get_env_bool("DRY_RUN", False)
        
        # --- Validate log level ---
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise SettingsError(f"Invalid LOG_LEVEL: {self.log_level}")

    def _get_env(self, key: str, default: str = None, required: bool = False) -> str:
        value = os.getenv(key, default)
        if required and (value is None or value == ""):
            raise SettingsError(f"Missing required environment variable: {key}")
        return value

    def _get_env_int(self, key: str, default: int) -> int:
        value = os.getenv(key)
        if value is None or value == "":
            return default
        try:
            return int(value)
        except ValueError:
            raise SettingsError(f"Invalid integer value for {key}: {value}")

    def _get_env_float(self, key: str, default: float) -> float:
        value = os.getenv(key)
        if value is None or value == "":
            return default
        try:
            return float(value)
        except ValueError:
            raise SettingsError(f"Invalid float value for {key}: {value}")

    def _get_env_bool(self, key: str, default: bool) -> bool:
        value = os.getenv(key)
        if value is None or value == "":
            return default
        return value.lower() in ["true", "1", "t", "y", "yes"]

# Create a single, importable instance of the settings
settings = Settings()