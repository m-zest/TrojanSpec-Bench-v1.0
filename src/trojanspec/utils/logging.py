"""Consistent, dependency-free logging for the pipeline."""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger. Level via ``TROJANSPEC_LOG_LEVEL`` env var."""
    global _CONFIGURED
    if not _CONFIGURED:
        level = os.environ.get("TROJANSPEC_LOG_LEVEL", "INFO").upper()
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root = logging.getLogger("trojanspec")
        root.setLevel(level)
        root.addHandler(handler)
        root.propagate = False
        _CONFIGURED = True
    return logging.getLogger(f"trojanspec.{name}")
