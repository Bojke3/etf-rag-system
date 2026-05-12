"""Evaluation layer - Metrics and benchmarking"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class Metric(ABC):
    """Abstract base class for metrics"""
    
    @abstractmethod
    def calculate(self, reference: str, candidate: str) -> float:
        """Calculate metric score"""
        pass

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
