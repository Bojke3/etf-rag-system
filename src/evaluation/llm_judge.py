"""LLM-as-a-judge evaluation metric.

Scores answer quality on a 0-5 scale by asking an LLM to compare a candidate
answer against the reference (expected) answer, following the approach in
Zheng et al. 2023 (MT-Bench / Chatbot Arena) and adapted for factual
single/multi-hop QA the way it is used in RAG evaluation papers (e.g.
Borovina & Misic, "Evaluating Multi-Hop QA Performance Across Vector-based,
Graph-based, and Hybrid RAG Architectures", INFOTEH-JAHORINA 2026).
"""

import logging
import re
from typing import Optional

from .base import Metric

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = """Ti si strog i precizan ocenjivac tacnosti odgovora RAG sistema \
koji odgovara na pitanja o pravilnicima Elektrotehnickog fakulteta.
Porediš ODGOVOR SISTEMA sa REFERENTNIM ODGOVOROM za dato PITANJE.
Ocenjuješ iskljucivo cinjenicnu tacnost i potpunost — ne stil, ne duzinu, ne pismo.
Vrati iskljucivo jedan broj od 0 do 5, bez ikakvog objasnjenja:
0 = potpuno netacno ili nepovezano sa referentnim odgovorom
1 = uglavnom netacno, tek delimicno relevantno
2 = delimicno tacno, nedostaju bitne informacije
3 = uglavnom tacno, ali sa manjim netacnostima ili izostavljenim detaljima
4 = tacno i potpuno, sitne razlike u formulaciji koje ne menjaju znacenje
5 = potpuno tacno i potpuno, znacenjski ekvivalentno referentnom odgovoru"""

JUDGE_PROMPT = """Pitanje: {question}

Referentni (tacan) odgovor: {reference}

Odgovor sistema koji ocenjujes: {candidate}

Ocena (samo broj 0-5):"""

_SCORE_RE = re.compile(r"[0-5](?:\.\d+)?")


class LLMJudgeMetric(Metric):
    """Scores a candidate answer 0-5 against a reference answer using an LLM judge."""

    def __init__(self, llm_client, num_samples: int = 1):
        """llm_client: any object with .generate(prompt, system=..., temperature=...).
        num_samples: how many independent judge calls to average per answer
        (the reference paper uses 3 differently-formulated prompts to reduce
        scoring variance; default is 1 to keep local CPU inference cheap)."""
        self.llm_client = llm_client
        self.num_samples = max(1, num_samples)

    def calculate(self, reference: str, candidate: str, question: str = "") -> float:
        """Return the averaged judge score (0-5). Falls back to 0.0 if the
        judge model never returns a parseable score."""
        scores = []
        for _ in range(self.num_samples):
            score = self._score_once(question, reference, candidate)
            if score is not None:
                scores.append(score)

        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def _score_once(self, question: str, reference: str, candidate: str) -> Optional[float]:
        prompt = JUDGE_PROMPT.format(question=question, reference=reference, candidate=candidate)
        try:
            response = self.llm_client.generate(
                prompt,
                system=JUDGE_SYSTEM,
                temperature=0.0,
                max_tokens=10,
            )
        except Exception as e:
            logger.error(f"Error calling LLM judge: {e}")
            return None

        match = _SCORE_RE.search(response or "")
        if not match:
            logger.warning(f"LLM judge returned unparsable score: {response!r}")
            return None

        return max(0.0, min(5.0, float(match.group())))
