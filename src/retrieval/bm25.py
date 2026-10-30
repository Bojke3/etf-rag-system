"""Deterministic lexical BM25 over original chunk text; standard library only.

Positive IDF: log(1 + (N-df+0.5)/(df+0.5)); k1=1.2, b=0.75.
Unique query terms, no stemming, stopword removal, expansion or reranking.
"""
from collections import Counter, defaultdict
import math
import re
import unicodedata

from .base import Retriever

TOKENIZER_VERSION = "serbian_latin_ascii_alnum_v1"
_CYRILLIC = dict(zip("абвгдђежзијклљмнњопрстћуфхцчџш",
                     ("a", "b", "v", "g", "d", "dj", "e", "z", "z", "i", "j", "k", "l", "lj", "m", "n", "nj", "o", "p", "r", "s", "t", "c", "u", "f", "h", "c", "c", "dz", "s")))


def tokenize(text):
    text = "".join(_CYRILLIC.get(c, c) for c in unicodedata.normalize("NFC", text).casefold()).replace("đ", "dj")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", text)


class BM25Retriever(Retriever):
    def __init__(self, chunks, k1=1.2, b=0.75):
        if not math.isfinite(k1) or k1 < 0 or not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("BM25 requires finite k1 >= 0 and 0 <= b <= 1.")
        if not chunks:
            raise ValueError("BM25 needs a nonempty corpus.")
        self.chunks = [dict(c) for c in chunks]
        self.k1, self.b = k1, b
        self.postings = defaultdict(list)
        self.lengths = []
        for i, chunk in enumerate(self.chunks):
            terms = Counter(tokenize(chunk["text"]))
            self.lengths.append(sum(terms.values()))
            for term, tf in terms.items():
                self.postings[term].append((i, tf))
        self.avgdl = sum(self.lengths) / len(self.chunks)
        if self.avgdl == 0:
            raise ValueError("Corpus contains no indexable tokens.")

    def retrieve(self, query, top_k=5):
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k must be a positive integer.")
        scores = defaultdict(float)
        for term in sorted(set(tokenize(query))):
            hits = self.postings.get(term, [])
            if not hits:
                continue
            idf = math.log1p((len(self.chunks) - len(hits) + .5) / (len(hits) + .5))
            for i, tf in hits:
                denominator = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avgdl)
                scores[i] += idf * tf * (self.k1 + 1) / denominator
        # Do not pad no-overlap queries with arbitrary zero-score documents.
        ranking = sorted(scores, key=lambda i: (-scores[i], i))[:top_k]
        return [{**self.chunks[i], "score": scores[i]} for i in ranking]
