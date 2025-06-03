"""
Configuration loading and proxy setup.
"""
import json
import os
from loguru import logger


def load_config(config_path: str = "config.json") -> dict:
    """
    Load bot configuration from a JSON file.

    :param config_path: Path to the configuration file.
    :return: Configuration dictionary.
    :raises FileNotFoundError: If the config file is not found.
    :raises json.JSONDecodeError: If the file contains invalid JSON.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


def get_proxy_url(proxy_config: dict) -> str:
    """
    Get the proxy URL from the configuration.

    :param proxy_config: Dictionary containing proxy settings.
    :return: Formatted proxy URL or an empty string if not configured.
    """
    if not proxy_config.get("status", False):
        return ""

    proxy_type = proxy_config.get("type")
    host = proxy_config.get("host")
    port = proxy_config.get("port")
    username = proxy_config.get("username")
    password = proxy_config.get("password")

    if proxy_type not in ("http", "socks4", "socks5"):
        return ""

    if username and password:
        proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
    else:
        proxy_url = f"{proxy_type}://{host}:{port}"

    return proxy_url