"""Canonical public coverage entry point; no parallel starter heuristic."""
from .model import assess, sensor_gaps


def assess_observability(available):
    return assess(list(available))


__all__ = ['assess_observability', 'sensor_gaps']
