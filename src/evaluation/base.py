"""Base interfaces for evaluation metrics."""

from abc import ABC, abstractmethod


class Metric(ABC):
    """Abstract base class for metrics"""

    @abstractmethod
    def calculate(self, reference: str, candidate: str) -> float:
        """Calculate metric score"""
        pass
