import json
import re
import logging
from typing import Optional, Dict
from ...llm.inference import LLMInference

try:
    from ...verification.nli_faithfulness import NLIFaithfulnessScorer
except ImportError:
    NLIFaithfulnessScorer = None

logger = logging.getLogger(__name__)

class RAGASEvaluator:
    """
    LLM-assisted evaluator that computes RAGAS-like metrics:
    - Faithfulness (Factual Consistency)
    - Answer Relevance
    - Context Recall (requires Ground Truth)
    """
    def __init__(self, llm: LLMInference):
        self.llm = llm
        if NLIFaithfulnessScorer is not None:
            self.nli_scorer = NLIFaithfulnessScorer()
        else:
            self.nli_scorer = None

    def score_faithfulness(self, answer: str, context: str) -> Optional[float]:
        """
        Rate faithfulness (factual consistency) of the answer against retrieved context.
        Returns score in range [0.0, 1.0].
        """
        if not answer or not answer.strip() or not context or not context.strip():
            return 1.0

        prompt = f"""Given the following context and answer, extract every factual claim from the answer. For each claim, state whether it is SUPPORTED or NOT SUPPORTED by the context. Output ONLY a valid JSON array of objects with keys 'claim' and 'verdict' where 'verdict' is either 'SUPPORTED' or 'NOT_SUPPORTED'. Do not output any explanation, preamble, markdown formatting (like ```json), or backticks.

Context:
{context}

Answer:
{answer}

JSON Output:"""

        try:
            response = self.llm.generate(prompt=prompt, max_tokens=512)
            # Remove possible markdown fences
            clean_res = response.strip()
            if clean_res.startswith("```"):
                # strip out ```json or ``` lines
                lines = clean_res.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_res = "\n".join(lines).strip()

            data = json.loads(clean_res)
            if not isinstance(data, list) or not data:
                return 1.0

            supported_count = 0
            total_count = 0
            for item in data:
                if isinstance(item, dict) and "verdict" in item:
                    total_count += 1
                    if item["verdict"].upper() == "SUPPORTED":
                        supported_count += 1

            if total_count == 0:
                return 1.0
            return float(supported_count / total_count)
        except Exception as e:
            logger.error(f"Error computing faithfulness: {e}. Raw response: {response if 'response' in locals() else 'None'}")
            # Regex fallback
            try:
                verdicts = re.findall(r'"verdict"\s*:\s*"([^"]+)"', response)
                if verdicts:
                    supported = sum(1 for v in verdicts if v.upper() == "SUPPORTED")
                    return float(supported / len(verdicts))
            except Exception:
                pass
            return 0.5

    def score_answer_relevance(self, query: str, answer: str) -> Optional[float]:
        """
        Rate answer relevance to the user query on a scale of 0.0 to 1.0.
        """
        if not query or not query.strip() or not answer or not answer.strip():
            return 0.0

        prompt = f"""Given the question and the answer, rate how relevant the answer is to the question on a scale of 0.0 to 1.0. An answer is relevant if it directly addresses the query, regardless of correctness. Output ONLY a single decimal number between 0.0 and 1.0, with no explanation, preamble, or other text.

Question: {query}
Answer: {answer}

Relevance Score:"""

        try:
            response = self.llm.generate(prompt=prompt, max_tokens=50).strip()
            match = re.search(r"(\d+\.\d+|\d+)", response)
            if match:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))
            return 0.5
        except Exception as e:
            logger.error(f"Error computing answer relevance: {e}")
            return 0.5

    def score_context_recall(self, query: str, context: str, ground_truth: str) -> Optional[float]:
        """
        Rate context recall (ground truth facts present in retrieved context) in range [0.0, 1.0].
        """
        if not ground_truth or not ground_truth.strip():
            return None

        if not context or not context.strip():
            return 0.0

        prompt = f"""Given the question, the retrieved context, and the ground truth answer, determine what fraction of the facts in the ground truth are present in the context. Output ONLY a single decimal number between 0.0 and 1.0 with no explanation, preamble, or other text.

Question: {query}
Retrieved Context: {context}
Ground Truth: {ground_truth}

Recall Score:"""

        try:
            response = self.llm.generate(prompt=prompt, max_tokens=50).strip()
            match = re.search(r"(\d+\.\d+|\d+)", response)
            if match:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))
            return 0.5
        except Exception as e:
            logger.error(f"Error computing context recall: {e}")
            return 0.5

    def evaluate(self, query: str, answer: str, context: str, ground_truth: str = "") -> Dict[str, Optional[float]]:
        """
        Run all evaluations and return a dict of scores.
        """
        f_score = self.score_faithfulness(answer, context)
        ar_score = self.score_answer_relevance(query, answer)
        cr_score = self.score_context_recall(query, context, ground_truth)

        nli_score = None
        if self.nli_scorer and self.nli_scorer.is_loaded:
            try:
                nli_result = self.nli_scorer.score(answer, context)
                nli_score = nli_result.get("faithfulness_nli")
            except Exception as e:
                logger.error(f"NLI evaluation failed: {e}")

        return {
            "faithfulness": f_score,
            "answer_relevance": ar_score,
            "context_recall": cr_score,
            "nli_faithfulness": nli_score
        }
