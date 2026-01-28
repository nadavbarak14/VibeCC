"""Centralized logging configuration for VibeCC.

Provides rotating file logs with consistent formatting across all components.
"""

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Default configuration
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "vibecc.log"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_LOG_LEVEL = "INFO"

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: str | Path | None = None,
    log_file: str = DEFAULT_LOG_FILE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    level: str | None = None,
    console: bool = True,
) -> logging.Logger:
    """Set up logging with rotating file handler.

    Args:
        log_dir: Directory for log files. Defaults to 'logs' in current directory.
                 Can be overridden with VIBECC_LOG_DIR environment variable.
        log_file: Log file name. Defaults to 'vibecc.log'.
        max_bytes: Maximum size per log file before rotation. Defaults to 10MB.
        backup_count: Number of backup files to keep. Defaults to 5.
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.
               Can be overridden with VIBECC_LOG_LEVEL environment variable.
        console: Whether to also log to console. Defaults to True.

    Returns:
        The root vibecc logger.
    """
    # Determine log directory
    if log_dir is None:
        log_dir = os.environ.get("VIBECC_LOG_DIR", DEFAULT_LOG_DIR)
    log_dir = Path(log_dir)

    # Create log directory if needed
    log_dir.mkdir(parents=True, exist_ok=True)

    # Determine log level
    if level is None:
        level = os.environ.get("VIBECC_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Get the vibecc root logger
    logger = logging.getLogger("vibecc")
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Add rotating file handler
    log_path = log_dir / log_file
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Log startup
    logger.info("VibeCC logging initialized (level=%s, file=%s)", level, log_path)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a component.

    Args:
        name: Component name (e.g., 'orchestrator', 'git_manager').
              Will be prefixed with 'vibecc.'.

    Returns:
        Logger instance for the component.
    """
    if not name.startswith("vibecc."):
        name = f"vibecc.{name}"
    return logging.getLogger(name)


def truncate_output(output: str, max_length: int = 5000) -> str:
    """Truncate long output for logging.

    Args:
        output: The output string to truncate.
        max_length: Maximum length before truncation.

    Returns:
        Truncated string with indicator if truncated.
    """
    if len(output) <= max_length:
        return output
    return output[:max_length] + f"\n... [truncated, {len(output) - max_length} more chars]"


def sanitize_for_log(text: str) -> str:
    """Remove sensitive data from log output.

    Args:
        text: Text that may contain sensitive data.

    Returns:
        Sanitized text safe for logging.
    """
    # Patterns for sensitive data
    patterns = [
        (r"ghp_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),  # GitHub PAT
        (r"gho_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),  # GitHub OAuth
        (r"github_pat_[a-zA-Z0-9_]{82}", "[GITHUB_TOKEN]"),  # Fine-grained PAT
        (r"Bearer [a-zA-Z0-9._-]+", "Bearer [REDACTED]"),  # Bearer tokens
        (r"token=[a-zA-Z0-9._-]+", "token=[REDACTED]"),  # Query param tokens
    ]

    result = text
    for pat, replacement in patterns:
        result = re.sub(pat, replacement, result)

    return result
