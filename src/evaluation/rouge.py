"""ROUGE evaluation metric."""

from typing import Dict
import logging

from .base import Metric

logger = logging.getLogger(__name__)


class ROUGEMetric(Metric):
    """ROUGE metric implementation"""

    def calculate(self, reference: str, candidate: str) -> Dict[str, float]:
        """Calculate ROUGE scores"""
        try:
            from rouge_score import rouge_scorer

            scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
            scores = scorer.score(reference, candidate)

            return {
                'rouge1': scores['rouge1'].fmeasure,
                'rouge2': scores['rouge2'].fmeasure,
                'rougeL': scores['rougeL'].fmeasure,
            }
        except Exception as e:
            logger.error(f"Error calculating ROUGE: {e}")
            return {'rouge1': 0.0, 'rouge2': 0.0, 'rougeL': 0.0}
