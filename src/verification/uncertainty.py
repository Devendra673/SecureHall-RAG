import logging
import re
from typing import Tuple

logger = logging.getLogger("securehall-rag.uncertainty")

class UncertaintyQuantifier:
    """
    Quantifies uncertainty in RAG pipeline responses and attaches appropriate warnings or disclaimers.
    """
    
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    ABSTAIN = "ABSTAIN"

    # Query Type Detection Patterns
    QUERY_TYPES = {
        "factual": [
            r"\b(what is|what are|who is|when (is|was|does)|how many|how much)\b",
            r"\b(define|definition of|meaning of)\b",
            r"\b(list|name|give me|tell me)\b.*\b(all|the|every)\b",
        ],
        "procedural": [
            r"\b(how (do|to|can|should)|steps to|process for|procedure)\b",
            r"\b(apply for|submit|request|file|raise)\b",
        ],
        "comparative": [
            r"\b(difference between|compare|versus|vs\.?|better|worse|more|less)\b",
            r"\b(which (is|are|has))\b.*\bdifference\b",
        ],
        "policy": [
            r"\b(allowed|permitted|prohibited|can i|am i allowed|is it okay)\b",
            r"\b(policy|rule|regulation|entitled|entitlement)\b",
        ],
    }

    # Threshold Configurations per Query Type
    THRESHOLDS = {
        "factual":    {"HIGH": 0.80, "MODERATE": 0.58, "LOW": 0.38},
        "procedural": {"HIGH": 0.72, "MODERATE": 0.52, "LOW": 0.35},
        "comparative":{"HIGH": 0.68, "MODERATE": 0.48, "LOW": 0.32},
        "policy":     {"HIGH": 0.78, "MODERATE": 0.56, "LOW": 0.38},
        "default":    {"HIGH": 0.75, "MODERATE": 0.50, "LOW": 0.35},
    }

    @classmethod
    def classify_query(cls, query: str) -> str:
        """Classifies the query type based on patterns."""
        if not query:
            return "default"
        query_lower = query.lower()
        for qtype, patterns in cls.QUERY_TYPES.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return qtype
        return "default"

    @classmethod
    def get_tier(cls, confidence: float, query: str = "") -> str:
        """
        Determines the uncertainty tier based on the confidence score and query type.
        """
        qtype = cls.classify_query(query)
        thresholds = cls.THRESHOLDS[qtype]

        if confidence >= thresholds["HIGH"]:
            return cls.HIGH
        elif confidence >= thresholds["MODERATE"]:
            return cls.MODERATE
        elif confidence >= thresholds["LOW"]:
            return cls.LOW
        else:
            return cls.ABSTAIN

    @classmethod
    def process_response(cls, answer: str, confidence: float, query: str = "") -> Tuple[str, str]:
        """
        Processes answer text and confidence, returns (processed_answer, uncertainty_tier).
        
        Rules:
        - HIGH: Keep as is.
        - MODERATE: Keep as is.
        - LOW: Keep but append warning disclaimer.
        - ABSTAIN: Replace answer with abstention disclaimer.
        """
        tier = cls.get_tier(confidence, query)
        
        if tier == cls.HIGH:
            return answer, tier
            
        elif tier == cls.MODERATE:
            return answer, tier
            
        elif tier == cls.LOW:
            disclaimer = "\n\n*Note: This answer was generated with low confidence from the source documents. Please verify with official channels.*"
            if not answer.endswith(disclaimer):
                answer = answer.strip() + disclaimer
            return answer, tier
            
        else: # ABSTAIN
            abstain_msg = "I apologize, but I cannot find sufficient reliable evidence in the provided documents to answer your question with confidence."
            return abstain_msg, tier
