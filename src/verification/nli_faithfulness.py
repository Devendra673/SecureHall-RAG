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
    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-small", device: str = "cpu"):
        self.model_name = model_name
        self.model = None

        if CrossEncoder is not None:
            try:
                logger.info(f"Loading NLI model: {model_name} on {device}")
                self.model = CrossEncoder(model_name, device=device)
                logger.info("NLI model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load NLI model {model_name}: {e}")
        else:
            logger.warning("sentence-transformers not installed. NLI Faithfulness Scorer disabled.")

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

            # Prepare pairs of (context/premise, sentence/hypothesis)
            pairs = [(context, sentence) for sentence in sentences]

            # CrossEncoder outputs raw logits for [contradiction, entailment, neutral]
            # cross-encoder/nli-deberta-v3-small outputs: label 0: contradiction, label 1: entailment, label 2: neutral
            logits = self.model.predict(pairs)

            sentence_scores = []
            entailment_probabilities = []

            for i, logit_row in enumerate(logits):
                # Apply Softmax to logits to get probabilities
                exp_logits = np.exp(logit_row - np.max(logit_row))  # stable softmax
                probs = exp_logits / np.sum(exp_logits)

                prob_contradiction = float(probs[0])
                prob_entailment = float(probs[1])
                prob_neutral = float(probs[2])

                entailment_probabilities.append(prob_entailment)

                sentence_scores.append({
                    "sentence": sentences[i],
                    "entailment": prob_entailment,
                    "contradiction": prob_contradiction,
                    "neutral": prob_neutral,
                    "nli_label": "entailment" if prob_entailment > prob_contradiction and prob_entailment > prob_neutral 
                                 else "contradiction" if prob_contradiction > prob_neutral 
                                 else "neutral"
                })

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
