"""
Configuration package.

Exposes the application settings instance and getter function.
Import settings from here rather than from the module directly
to keep import paths stable if internals are reorganized.
"""

from app.config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
