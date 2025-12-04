"""
Configuration loader for scheduler settings.
"""
import json
import os
from typing import Dict, Optional

CONFIG_FILE = "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "scheduler": {
        "enabled": True,
        "market_hours": {
            "start": "09:30",
            "end": "16:00",
            "timezone": "America/New_York",
            "fetch_interval_minutes": 30
        },
        "after_market": {
            "enabled": True,
            "times": ["20:00", "06:00"],
            "timezone": "America/New_York"
        },
        "weekends": {
            "enabled": True,
            "fetch_time": "20:00",
            "timezone": "America/New_York"
        },
        "holidays": {
            "enabled": True
        },
        "retry": {
            "max_attempts": 3,
            "backoff_seconds": 60
        }
    }
}


def load_config() -> Dict:
    """
    Load configuration from config.json file.
    Returns default config if file doesn't exist or is invalid.
    """
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Merge with defaults to ensure all keys exist
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        
        # Deep merge scheduler config
        if "scheduler" in config:
            merged_config["scheduler"].update(config["scheduler"])
            for key in ["market_hours", "after_market", "weekends", "holidays", "retry"]:
                if key in config["scheduler"]:
                    merged_config["scheduler"][key].update(config["scheduler"][key])
        
        return merged_config
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARNING] Failed to load config.json: {e}, using defaults")
        return DEFAULT_CONFIG.copy()


def get_scheduler_config() -> Dict:
    """Get scheduler configuration section."""
    config = load_config()
    return config.get("scheduler", DEFAULT_CONFIG["scheduler"])


def is_scheduler_enabled() -> bool:
    """Check if scheduler is enabled."""
    scheduler_config = get_scheduler_config()
    return scheduler_config.get("enabled", True)

