"""BERTScore evaluation metric."""

from typing import Dict
import logging

from .base import Metric

logger = logging.getLogger(__name__)


class BERTScoreMetric(Metric):
    """BERTScore metric implementation"""

    def calculate(self, reference: str, candidate: str) -> Dict[str, float]:
        """Calculate BERTScore"""
        try:
            from bert_score import score

            P, R, F1 = score([candidate], [reference], lang='en', verbose=False)

            return {
                'precision': float(P[0]),
                'recall': float(R[0]),
                'f1': float(F1[0]),
            }
        except Exception as e:
            logger.error(f"Error calculating BERTScore: {e}")
            return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
