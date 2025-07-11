import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import streamlit as st


# --- Project Root Detection ---
def get_project_root() -> Path:
    """
    Determines the project root directory by locating pyproject.toml.
    Returns:
        Path: The absolute path to the project root directory.
    """
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError(
        "Could not locate pyproject.toml to determine project root."
    )


PROJECT_ROOT = get_project_root()

# --- Configuration File Paths ---
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Ensure config and log directories exist
CONFIG_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# --- Logger Setup ---
def setup_logger(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Sets up the root logger with console and file handlers.
    Args:
        log_level (str): Logging level (e.g., "DEBUG", "INFO").
        log_to_file (bool): Whether to log to a file in addition to console.
    Returns:
        logging.Logger: Configured root logger.
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    logger.handlers.clear()
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    if log_to_file:
        log_file = LOG_DIR / f"election_dashboard_.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


# --- Configuration Loading ---
@st.cache_data(ttl=300)
def load_config(config_file: Path = CONFIG_FILE) -> Dict:
    """
    Loads the configuration from a JSON file, creating it with defaults if it doesn't exist.
    Args:
        config_file (Path): Path to the configuration file.
    Returns:
        Dict: Configuration dictionary.
    """
    if not config_file.exists():
        logging.warning(
            f"Configuration file '{config_file}' not found. Creating with default values."
        )
        try:
            with open(config_file, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            logging.info(f"Created default configuration file at '{config_file}'")
        except Exception as e:
            logging.error(f"Failed to create configuration file '{config_file}': {e}")
            return DEFAULT_CONFIG

    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.error(
            f"Configuration file '{config_file}' is not valid JSON. Using default config."
        )
        return DEFAULT_CONFIG


# --- Default Configuration ---
DEFAULT_CONFIG = {
    "election_year": datetime.now().year,
    "current_election_type": "national",
    "data_files": {
        "national": "national_election_results.csv",
        "local": "local_election_results.csv",
        "barangay": "barangay_election_results.csv",
    },
    "log_level": "INFO",
    "cache_ttl": 300,
}

# Initialize logger
logger = setup_logger(log_level=DEFAULT_CONFIG["log_level"])
