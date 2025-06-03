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


def setup_proxy_environment(proxy_config: dict) -> bool:
    """
    Configure HTTP/SOCKS proxy environment variables based on provided settings.

    :param proxy_config: Dictionary containing proxy settings.
    :return: True if proxy was enabled; False otherwise.
    """
    if not proxy_config.get("status", False):
        return False

    proxy_type = proxy_config.get("type")
    host = proxy_config.get("host")
    port = proxy_config.get("port")
    username = proxy_config.get("username")
    password = proxy_config.get("password")

    if proxy_type not in ("http", "socks4", "socks5"):
        return False

    if username and password:
        proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
    else:
        proxy_url = f"{proxy_type}://{host}:{port}"

    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

    logger.info(f"Proxy configured: {proxy_url}")
    return True