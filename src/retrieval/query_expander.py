"""
Query Expander — generates alternative phrasings to improve retrieval recall.
"""
import logging
import re

logger = logging.getLogger("securehall-rag.query_expander")

class QueryExpander:
    def __init__(self, llm_client):
        self.llm = llm_client

    def expand(self, query: str, n: int = 2) -> list[str]:
        """
        Returns [original_query] + n alternative phrasings.
        If LLM fails, returns only [original_query].
        """
        if not self.llm or not getattr(self.llm, "is_loaded", False):
            return [query]
            
        # Avoid expanding very short queries
        if len(query.split()) <= 4:
            return [query]

        prompt = f"""Generate {n} alternative ways to ask the following question.
Each alternative should use different words but ask the same thing.
Output ONLY the alternatives, one per line. No numbering, no explanation.

Question: {query}
Alternatives:"""
        try:
            response = self.llm.generate(prompt, max_tokens=100, temperature=0.3)
            lines = [l.strip() for l in response.strip().split("\n") if l.strip()]
            
            # Clean lines of any numbers (e.g. "1. alternate query")
            cleaned_alternatives = []
            for line in lines:
                cleaned = re.sub(r'^\d+\.\s*', '', line).strip()
                if cleaned:
                    cleaned_alternatives.append(cleaned)
                    
            alternatives = cleaned_alternatives[:n]
            logger.debug(f"Query expanded: {query!r} → {alternatives}")
            return [query] + alternatives
        except Exception as e:
            logger.warning(f"Query expansion failed: {e} — using original query only")
            return [query]
