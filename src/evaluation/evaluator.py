"""Combined evaluator for answer quality metrics."""

from typing import Dict

from .bertscore import BERTScoreMetric
from .bleu import BLEUMetric
from .rouge import ROUGEMetric


class Evaluator:
    """Main evaluator combining multiple metrics"""

    def __init__(self):
        self.bleu_metric = BLEUMetric()
        self.rouge_metric = ROUGEMetric()
        self.bertscore_metric = BERTScoreMetric()

    def evaluate(self, reference: str, candidate: str) -> Dict[str, float]:
        """Evaluate answer quality"""
        results = {
            'bleu': self.bleu_metric.calculate(reference, candidate),
            'rouge': self.rouge_metric.calculate(reference, candidate),
            'bertscore': self.bertscore_metric.calculate(reference, candidate),
        }
        return results
