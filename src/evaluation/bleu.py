"""BLEU evaluation metric."""

import logging

from .base import Metric

logger = logging.getLogger(__name__)


class BLEUMetric(Metric):
    """BLEU metric implementation"""

    def calculate(self, reference: str, candidate: str) -> float:
        """Calculate BLEU score"""
        try:
            from nltk.translate.bleu_score import sentence_bleu
            from .rouge import _tokenize

            ref_tokens = _tokenize(reference)
            cand_tokens = _tokenize(candidate)

            score = sentence_bleu([ref_tokens], cand_tokens, weights=(0.25, 0.25, 0.25, 0.25))
            return float(score)
        except Exception as e:
            logger.error(f"Error calculating BLEU: {e}")
            raise RuntimeError(f"BLEU calculation failed: {e}") from e
