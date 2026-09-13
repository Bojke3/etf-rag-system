"""BERTScore evaluation metric."""

from typing import Dict
import logging

from .base import Metric

logger = logging.getLogger(__name__)


class BERTScoreMetric(Metric):
    """BERTScore metric implementation"""

    def __init__(self, model_type="bert-base-multilingual-cased", device="cpu"):
        self.model_type = model_type
        self.device = device
        self._scorer = None

    def calculate(self, reference: str, candidate: str) -> Dict[str, float]:
        """Calculate BERTScore"""
        try:
            from bert_score import BERTScorer
            if self._scorer is None:
                self._scorer = BERTScorer(model_type=self.model_type, lang="sr", device=self.device,
                                          rescale_with_baseline=False)
            P, R, F1 = self._scorer.score([candidate], [reference])

            return {
                'precision': float(P[0]),
                'recall': float(R[0]),
                'f1': float(F1[0]),
                'model_type': self.model_type,
                'configuration_hash': self._scorer.hash,
            }
        except Exception as e:
            logger.error(f"Error calculating BERTScore: {e}")
            return {'error': str(e)}
