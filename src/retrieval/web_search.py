import os
import requests
import logging

logger = logging.getLogger("securehall-rag.retrieval.web_search")

class WebSearchService:
    """
    Search service facilitating web search fallback for LLM query augmentation.
    Supports Google Custom Search Engine (CSE) and falls back to DuckDuckGo search.
    """

    def __init__(self):
        # Read keys from environment
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cx = os.getenv("GOOGLE_CX")

    def search(self, query: str, num_results: int = 3) -> list[dict]:
        """
        Execute web search query.
        
        Args:
            query: The search term or question.
            num_results: Max number of search results to return.
            
        Returns:
            List of dictionaries, each containing:
            - 'title': Page title.
            - 'link': Page URL.
            - 'snippet': Short text snippet.
        """
        results = []

        # 1. Try Google Custom Search JSON API if keys are configured
        if self.google_api_key and self.google_cx:
            try:
                logger.info("Triggering Google Custom Search Engine...")
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.google_api_key,
                    "cx": self.google_cx,
                    "q": query,
                    "num": num_results
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        results.append({
                            "title": item.get("title", "No Title"),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", "No Content Excerpt")
                        })
                    logger.info(f"Google CSE returned {len(results)} results.")
                    if results:
                        return results
                else:
                    logger.warning(
                        f"Google CSE returned status {response.status_code}. "
                        f"Response: {response.text[:200]}"
                    )
            except Exception as google_err:
                logger.error(f"Google CSE search error: {google_err}")

        # 2. Fallback to DuckDuckGo (Free, no credentials needed)
        try:
            logger.info("Triggering DuckDuckGo Search Fallback...")
            from ddgs import DDGS
            
            with DDGS() as ddgs:
                ddg_results = ddgs.text(query, max_results=num_results)
                
                # ddg_results is typically a list or generator of dicts
                for r in ddg_results:
                    title = r.get("title", "No Title")
                    link = r.get("href", r.get("link", ""))
                    snippet = r.get("body", r.get("snippet", "No Content Excerpt"))
                    
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
            logger.info(f"DuckDuckGo returned {len(results)} results.")
            return results
        except Exception as ddg_err:
            logger.error(f"DuckDuckGo search fallback failed: {ddg_err}")

        return results

# Test execution if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = WebSearchService()
    print("Testing DuckDuckGo search for 'FastAPI streaming SSE'...")
    res = service.search("FastAPI streaming SSE", num_results=2)
    for r in res:
        print("-" * 50)
        print("Title:", r["title"])
        print("Link:", r["link"])
        print("Snippet:", r["snippet"])
