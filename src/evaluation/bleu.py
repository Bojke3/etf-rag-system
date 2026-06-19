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
            from nltk.tokenize import word_tokenize

            ref_tokens = word_tokenize(reference.lower())
            cand_tokens = word_tokenize(candidate.lower())

            score = sentence_bleu([ref_tokens], cand_tokens, weights=(0.25, 0.25, 0.25, 0.25))
            return float(score)
        except Exception as e:
            logger.error(f"Error calculating BLEU: {e}")
            return 0.0
