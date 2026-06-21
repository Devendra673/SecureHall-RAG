"""
Task 4.1 Upgrade: LLM-Native Claim Splitter
Replaces the regex-based ClaimSplitter with an LLM prompt that extracts atomic claims in JSON.
"""

import json
import logging
import re
from typing import List, Optional

from src.verification.data_structures import Claim, SourceSpan
from src.llm.inference import LLMInference

logger = logging.getLogger(__name__)


class LLMClaimSplitter:
    """Splits LLM responses into atomic claims using an LLM prompt, falling back to regex."""

    def __init__(self, llm: Optional[LLMInference] = None):
        self.llm = llm
        self.claim_counter = 0

    def split_into_claims(self, text: str) -> List[Claim]:
        self.claim_counter = 0
        
        # Fast exit for short texts
        if len(text.strip()) < 10:
            return []

        claims = []
        if self.llm and self.llm.is_loaded:
            try:
                claims = self._split_with_llm(text)
            except Exception as e:
                logger.warning(f"LLM claim splitting failed, falling back to regex: {e}")
                claims = self._split_with_regex(text)
        else:
            claims = self._split_with_regex(text)

        # Build formal Claim objects
        result = []
        for c in claims:
            claim_text = c.get("claim", "").strip()
            if not claim_text or len(claim_text) < 5:
                continue
            
            # Optionally extract context sentence if provided
            original = c.get("original_sentence", claim_text)
            
            claim = Claim(
                claim_id=f"claim_{self.claim_counter:03d}",
                claim_text=claim_text,
                original_sentence=original,
                source_span=self._find_span(text, claim_text),
                context=original,
                sequence_order=self.claim_counter,
            )
            result.append(claim)
            self.claim_counter += 1

        return result

    def _split_with_llm(self, text: str) -> List[dict]:
        prompt = f"""You are an expert fact-checker. Your task is to break down the following text into a list of standalone, atomic factual claims.
An atomic claim is a single declarative sentence that contains exactly one fact or logical statement that can be independently verified.
Do NOT include conversational filler, greetings, or subjective opinions.

Format the output strictly as a JSON array of objects. Each object must have:
- "claim": The rewritten atomic claim.
- "original_sentence": The sentence from the text it was derived from.

Text to process:
{text}

Output JSON:"""
        
        response = self.llm.generate(prompt, max_tokens=1024)
        
        # Extract JSON from response (in case the model adds markdown formatting)
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                raise ValueError("Failed to parse LLM JSON output")
        else:
            raise ValueError("No JSON array found in LLM output")

    def _split_with_regex(self, text: str) -> List[dict]:
        # Fallback simplistic regex splitter
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        claims = []
        for s in sentences:
            # simple split by commas or conjunctions for clauses
            clauses = re.split(r";\s*|,\s+(?:and|but|or|also|however|therefore|thus)\s+", s)
            for c in clauses:
                claims.append({
                    "claim": c.strip(),
                    "original_sentence": s
                })
        return claims

    def _find_span(self, full_text: str, claim_text: str) -> Optional[SourceSpan]:
        normalized_text = full_text.lower()
        normalized_claim = claim_text.lower()
        start = normalized_text.find(normalized_claim)
        if start == -1:
            return None
        end = start + len(claim_text)
        return SourceSpan(start_pos=start, end_pos=end, text=full_text[start:end])

    def get_statistics(self) -> dict:
        return {"claims_generated": self.claim_counter}
