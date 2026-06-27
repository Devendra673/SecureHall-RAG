import logging
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

    @classmethod
    def get_tier(cls, confidence: float) -> str:
        """
        Determines the uncertainty tier based on the confidence score.
        """
        if confidence >= 0.75:
            return cls.HIGH
        elif confidence >= 0.50:
            return cls.MODERATE
        elif confidence >= 0.35:
            return cls.LOW
        else:
            return cls.ABSTAIN

    @classmethod
    def process_response(cls, answer: str, confidence: float) -> Tuple[str, str]:
        """
        Processes answer text and confidence, returns (processed_answer, uncertainty_tier).
        
        Rules:
        - HIGH: Keep as is.
        - MODERATE: Keep as is.
        - LOW: Keep but append warning disclaimer.
        - ABSTAIN: Replace answer with abstention disclaimer.
        """
        tier = cls.get_tier(confidence)
        
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
