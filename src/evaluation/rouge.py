"""ROUGE evaluation metric."""

from collections import Counter
from typing import Dict
import re

from .base import Metric

def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _ngram_counts(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def _f_measure(overlap: int, reference_total: int, candidate_total: int) -> float:
    if overlap == 0 or reference_total == 0 or candidate_total == 0:
        return 0.0

    precision = overlap / candidate_total
    recall = overlap / reference_total
    return 2 * precision * recall / (precision + recall)


def _lcs_length(reference: list[str], candidate: list[str]) -> int:
    previous = [0] * (len(candidate) + 1)
    for ref_token in reference:
        current = [0]
        for index, cand_token in enumerate(candidate, start=1):
            if ref_token == cand_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def _fallback_rouge(reference: str, candidate: str) -> Dict[str, float]:
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)

    ref_unigrams = _ngram_counts(ref_tokens, 1)
    cand_unigrams = _ngram_counts(cand_tokens, 1)
    unigram_overlap = sum((ref_unigrams & cand_unigrams).values())

    ref_bigrams = _ngram_counts(ref_tokens, 2)
    cand_bigrams = _ngram_counts(cand_tokens, 2)
    bigram_overlap = sum((ref_bigrams & cand_bigrams).values())

    lcs = _lcs_length(ref_tokens, cand_tokens)

    return {
        'rouge1': _f_measure(unigram_overlap, sum(ref_unigrams.values()), sum(cand_unigrams.values())),
        'rouge2': _f_measure(bigram_overlap, sum(ref_bigrams.values()), sum(cand_bigrams.values())),
        'rougeL': _f_measure(lcs, len(ref_tokens), len(cand_tokens)),
    }


class ROUGEMetric(Metric):
    """ROUGE metric implementation"""

    def calculate(self, reference: str, candidate: str) -> Dict[str, float]:
        """Use one Unicode-aware implementation regardless of installed packages.

        No English stemming or ASCII-only filtering. Different scripts still
        count as different lexical forms; this is not a semantic metric.
        """
        return _fallback_rouge(reference, candidate)
