"""
NLI-based Faithfulness Scorer
Phase 12: Academic Features

Computes factual consistency score between generated answer and context chunks
using a Natural Language Inference (NLI) model.
"""

import logging
from typing import Dict, List, Any
import numpy as np

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

try:
    import nltk
    # Lazy download if not already cached
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', quiet=True)
except ImportError:
    nltk = None

logger = logging.getLogger(__name__)

class NLIFaithfulnessScorer:
    # Sentence type classifications
    CLAIM_INDICATORS = [
        "must", "shall", "should", "required", "entitled", "prohibited",
        "cannot", "is not allowed", "days", "weeks", "months", "%", "₹", "$",
        "hours", "maximum", "minimum", "policy states", "according to"
    ]

    SKIP_PATTERNS = [
        r"^(additionally|furthermore|however|therefore|in summary|finally|in conclusion)",
        r"^(this means|as a result|for example|in other words)",
        r"^(the (above|following|document|policy))",
    ]

    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-base", device: str = None):
        self.model_name = model_name
        self.model = None
        self._cache = {}

        if device is None:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        if CrossEncoder is not None:
            try:
                logger.info(f"Loading NLI model: {model_name} on {device}")
                self.model = CrossEncoder(model_name, device=device)
                logger.info("NLI model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load NLI model {model_name}: {e}")
        else:
            logger.warning("sentence-transformers not installed. NLI Faithfulness Scorer disabled.")

    def _cache_key(self, sentence: str, context: str) -> str:
        import hashlib
        return hashlib.md5(f"{sentence[:200]}||{context[:500]}".encode()).hexdigest()

    def _is_claim_sentence(self, sentence: str) -> bool:
        """Returns True if sentence makes a verifiable factual claim."""
        import re
        sentence_lower = sentence.lower()
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, sentence_lower):
                return False
        if any(word in sentence_lower for word in self.CLAIM_INDICATORS):
            return True
        if any(c.isdigit() for c in sentence_lower):
            return True
        return False

    def _get_soft_label(self, entailment: float, sentence: str) -> str:
        """
        Returns action for this sentence:
        - 'keep'    : entailment >= 0.65, no action needed
        - 'warn'    : entailment 0.40–0.65, add inline warning
        - 'flag'    : entailment 0.25–0.40, add strong warning
        - 'redact'  : entailment < 0.25, genuine contradiction
        """
        if not self._is_claim_sentence(sentence):
            return "keep"
        if entailment >= 0.65:
            return "keep"
        elif entailment >= 0.40:
            return "warn"
        elif entailment >= 0.25:
            return "flag"
        else:
            return "redact"

    def score(self, answer: str, context: str) -> dict:
        """
        Score faithfulness/consistency of answer against context.
        Returns NLI score (0 to 1) and broken down sentence-level scores.
        """
        if self.model is None or not answer.strip() or not context.strip():
            return {"faithfulness_nli": 1.0, "sentence_scores": [], "model": self.model_name}

        try:
            # Tokenize into sentences
            if nltk is not None:
                sentences = nltk.sent_tokenize(answer)
            else:
                sentences = [s.strip() for s in answer.split('.') if s.strip()]

            # Filter out empty/too short sentences
            sentences = [s for s in sentences if len(s.split()) > 2]
            if not sentences:
                return {"faithfulness_nli": 1.0, "sentence_scores": [], "model": self.model_name}

            sentence_scores = []
            entailment_probabilities = []

            # Identify which sentences need checking vs cache vs skip
            pairs_to_predict = []
            pair_indices = []

            for i, sentence in enumerate(sentences):
                # Check cache first
                ckey = self._cache_key(sentence, context)
                if ckey in self._cache:
                    cached_val = self._cache[ckey]
                    prob_entailment = cached_val["entailment"]
                    prob_contradiction = cached_val["contradiction"]
                    prob_neutral = cached_val["neutral"]
                    entailment_probabilities.append(prob_entailment)
                    sentence_scores.append({
                        "sentence": sentence,
                        "entailment": prob_entailment,
                        "contradiction": prob_contradiction,
                        "neutral": prob_neutral,
                        "nli_label": "entailment" if prob_entailment > prob_contradiction and prob_entailment > prob_neutral 
                                     else "contradiction" if prob_contradiction > prob_neutral 
                                     else "neutral",
                        "is_claim": self._is_claim_sentence(sentence),
                        "soft_label": self._get_soft_label(prob_entailment, sentence)
                    })
                elif not self._is_claim_sentence(sentence):
                    # Skip NLI for non-claim sentences and assume full entailment
                    entailment_probabilities.append(1.0)
                    sentence_scores.append({
                        "sentence": sentence,
                        "entailment": 1.0,
                        "contradiction": 0.0,
                        "neutral": 0.0,
                        "nli_label": "entailment",
                        "is_claim": False,
                        "soft_label": "keep"
                    })
                else:
                    pairs_to_predict.append((context, sentence))
                    pair_indices.append(i)

            # Predict batch NLI scores
            if pairs_to_predict:
                logits = self.model.predict(pairs_to_predict, batch_size=8, show_progress_bar=False)

                for idx, logit_row in enumerate(logits):
                    exp_logits = np.exp(logit_row - np.max(logit_row))  # stable softmax
                    probs = exp_logits / np.sum(exp_logits)

                    prob_contradiction = float(probs[0])
                    prob_entailment = float(probs[1])
                    prob_neutral = float(probs[2])

                    entailment_probabilities.append(prob_entailment)
                    original_sentence = sentences[pair_indices[idx]]

                    score_data = {
                        "sentence": original_sentence,
                        "entailment": prob_entailment,
                        "contradiction": prob_contradiction,
                        "neutral": prob_neutral,
                        "nli_label": "entailment" if prob_entailment > prob_contradiction and prob_entailment > prob_neutral 
                                     else "contradiction" if prob_contradiction > prob_neutral 
                                     else "neutral",
                        "is_claim": True,
                        "soft_label": self._get_soft_label(prob_entailment, original_sentence)
                    }
                    sentence_scores.append(score_data)

                    # Save to cache
                    ckey = self._cache_key(original_sentence, context)
                    self._cache[ckey] = {
                        "entailment": prob_entailment,
                        "contradiction": prob_contradiction,
                        "neutral": prob_neutral
                    }

                    # Manage cache size
                    if len(self._cache) > 1000:
                        keys = list(self._cache.keys())
                        for k in keys[:200]:
                            del self._cache[k]

            # Overall score is the mean entailment probability
            overall_score = float(np.mean(entailment_probabilities)) if entailment_probabilities else 1.0

            return {
                "faithfulness_nli": overall_score,
                "sentence_scores": sentence_scores,
                "model": self.model_name
            }

        except Exception as e:
            logger.error(f"NLI Faithfulness scoring failed: {e}")
            return {"faithfulness_nli": 0.0, "sentence_scores": [], "model": self.model_name, "error": str(e)}

    @property
    def is_loaded(self) -> bool:
        return self.model is not None
