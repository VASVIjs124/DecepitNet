"""Monitoring package."""

from .monitor import SystemMonitor

try:
    from .dashboard import Dashboard
except ModuleNotFoundError:
    Dashboard = None  # type: ignore[assignment]

__all__ = ['SystemMonitor', 'Dashboard']
