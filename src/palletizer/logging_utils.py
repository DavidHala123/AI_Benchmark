"""Logging helpers shared by GUI components."""

from __future__ import annotations

import logging


LOGGER_NAME = "palletizer"


def configure_logger() -> logging.Logger:
    """Create and configure the shared application logger."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
