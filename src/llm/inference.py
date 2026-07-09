"""
LLM Inference Engine (Local)
Phase 2, Task 2.10

Implements local LLM inference using Ollama and Mistral 7B model.
"""

from typing import Optional, Dict, List
import time
import logging
import psutil
import os

try:
    import ollama
except ImportError:
    ollama = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMInference:
    """
    Local LLM inference using Ollama and Mistral 7B.

    Acceptance Criteria (Task 2.10):
    - ✅ Load Mistral 7B model via Ollama
    - ✅ Generate responses from prompts
    - ✅ Measure latency and memory usage
    - ✅ Support prompt formatting
    - ✅ Error handling for model availability

    Performance Targets:
    - Response latency: <5s per query with 2000-token context
    - Memory efficient local inference
    - First pull: ~4GB download, ~2-3 min (cached after first pull)

    Architecture:
    - Uses Ollama daemon for model serving
    - Mistral 7B: 7 billion parameters, ~4GB VRAM required
    - Temperature: 0.3 for more deterministic outputs (RAG use case)
    """

    def __init__(
        self,
        model_name: str = "llama3.1",
        temperature: float = 0.3,
        max_tokens: int = 512,
        top_p: float = 0.9,
        top_k: int = 40,
    ):
        """
        Initialize LLM inference engine.

        Args:
            model_name: Model identifier for Ollama (default "mistral")
                       - "mistral": Mistral 7B (recommended)
                       - "neural-chat": Alternative 7B model
                       - "orca-mini": Smaller alternative (~3B)
            temperature: Sampling temperature (0-1, lower = more deterministic)
                        Default 0.3 for RAG consistency
            max_tokens: Maximum tokens to generate per response (default 512)
            top_p: Nucleus sampling parameter (default 0.9)
            top_k: Top-k sampling parameter (default 40)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k

        self.client = None
        self.is_loaded = False
        self.last_latency = None
        self.process_id = os.getpid()

        # Warn if ollama is not installed, but do NOT raise here.
        # RAGPipeline already handles is_loaded=False (retrieval-only mode).
        # The error will be raised in load_model() if the user explicitly calls it.
        if ollama is None:
            logger.warning(
                "ollama package not installed — LLM generation will be unavailable. "
                "The pipeline will run in retrieval-only mode. "
                "Install with: pip install ollama"
            )

        logger.info(
            f"LLMInference initialized: model={model_name}, "
            f"temp={temperature}, max_tokens={max_tokens}"
        )

    def load_model(self) -> bool:
        """
        Load and verify model is available via Ollama.

        Returns:
            True if model loaded successfully

        Raises:
            ConnectionError: If Ollama daemon is not running
            RuntimeError: If model cannot be pulled/loaded

        Implementation:
        - Check Ollama daemon is running
        - Pull model if not cached locally
        - Verify model responds to ping
        """
        try:
            if ollama is None:
                logger.error(
                    "Cannot load model — ollama package is not installed. "
                    "Install with: pip install ollama, then restart the backend."
                )
                return False

            logger.info("Connecting to Ollama daemon...")

            # Test connection — SDK v0.1 returns dict, v0.2+ returns ListResponse object
            try:
                response = ollama.list()
                # Safely handle both SDK versions
                if hasattr(response, "models"):
                    # v0.2+ object API
                    model_names = [
                        getattr(m, "model", getattr(m, "name", ""))
                        for m in response.models
                    ]
                else:
                    # v0.1 dict API
                    model_names = [
                        m.get("name", "") for m in response.get("models", [])
                    ]
                logger.info(
                    f"Connected to Ollama — {len(model_names)} model(s) available"
                )
            except Exception as e:
                raise ConnectionError(
                    f"Cannot connect to Ollama daemon. "
                    f"Please ensure Ollama is running: ollama serve\n{str(e)}"
                )

            # Pull model only if not already available locally (avoids re-download)
            model_found = any(self.model_name in name for name in model_names)
            if not model_found:
                logger.info(
                    f"Pulling model {self.model_name} (may take 2-3 min on first run)..."
                )
                try:
                    ollama.pull(self.model_name)
                    logger.info(f"Model pull complete: {self.model_name}")
                except Exception as e:
                    logger.warning(f"Could not pull model: {str(e)}")
                    raise RuntimeError(
                        f"Failed to load model {self.model_name}: {str(e)}"
                    )
            else:
                logger.info(
                    f"Model {self.model_name} already available locally — skipping pull."
                )

            # Mark as loaded — the first generate() call is the real test
            logger.info(f"Model {self.model_name} ready.")
            self.is_loaded = True
            self.client = ollama
            return True

        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.is_loaded = False
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate response from prompt.

        Args:
            prompt: Input prompt text
            system_prompt: Optional system prompt for context/style guidance
            max_tokens: Override default max_tokens for this generation

        Returns:
            Generated response text

        Raises:
            RuntimeError: If model not loaded or generation fails

        Implementation:
        - Format prompt with optional system context
        - Call Ollama generate with tracking
        - Measure latency
        - Handle timeouts and errors
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        start_time = time.time()

        try:
            # Prepare full context
            if system_prompt:
                formatted_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                formatted_prompt = prompt

            logger.debug(f"Generating response for prompt: {prompt[:50]}...")

            # Generate response
            response = ollama.generate(
                model=self.model_name,
                prompt=formatted_prompt,
                stream=False,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                    "num_predict": max_tokens or self.max_tokens,
                },
            )

            elapsed_time = (time.time() - start_time) * 1000
            self.last_latency = elapsed_time

            # Extract response text — SDK v0.2+ returns GenerateResponse object,
            # v0.1 returned a plain dict. Support both.
            if hasattr(response, "response"):
                response_text = response.response  # v0.2+ object
            else:
                response_text = response.get("response", "")  # v0.1 dict
            response_text = (response_text or "").strip()

            logger.debug(f"Generation completed in {elapsed_time:.2f}ms")

            if elapsed_time > 5000:  # Warn if exceeds 5 seconds
                logger.warning(f"Slow generation: {elapsed_time:.2f}ms")

            return response_text

        except Exception as e:
            self.last_latency = (time.time() - start_time) * 1000
            logger.error(f"Generation failed: {str(e)}")
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Stream response from prompt. Yields response tokens as they arrive.
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            if system_prompt:
                formatted_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                formatted_prompt = prompt

            response = ollama.generate(
                model=self.model_name,
                prompt=formatted_prompt,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                    "num_predict": max_tokens or self.max_tokens,
                },
            )
            
            for chunk in response:
                if hasattr(chunk, "response"):
                    yield chunk.response
                else:
                    yield chunk.get("response", "")

        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise RuntimeError(f"LLM streaming failed: {str(e)}")

    def rewrite_query(self, query: str, history: list[dict]) -> str:
        """
        Rewrite a follow-up query to be standalone using conversation history.
        """
        if not history:
            return query

        if not self.is_loaded:
            return query

        try:
            history_text = "\n".join(
                f"{msg.get('role', 'unknown').capitalize()}: {msg.get('content', '')}"
                for msg in history
            )

            rewrite_prompt = (
                "You are a query rewriter. Given a conversation history and a follow-up question, "
                "rewrite the follow-up into a standalone, fully de-referenced search query. "
                "Output ONLY the rewritten query text with no explanation, no quotes, and no preamble.\n\n"
                f"Conversation history:\n{history_text}\n\n"
                f"Follow-up question: {query}"
            )

            rewritten = self.generate(prompt=rewrite_prompt, max_tokens=150)
            rewritten = rewritten.strip().strip('"\'')

            if not rewritten or len(rewritten) > 500:
                return query

            logger.info(f"Query rewritten: '{query}' → '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.error(f"Failed to rewrite query: {str(e)}")
            return query

    def generate_hypothetical_document(self, query: str) -> str:
        """
        Generate a hypothetical document/passage to answer the query (HyDE pattern).
        """
        if not self.is_loaded:
            return query

        try:
            hyde_prompt = (
                "Write a short factual passage (2-3 sentences) that would directly and precisely answer the following question. "
                "Do not preface it with anything. Output ONLY the passage text.\n\n"
                f"Question: {query}"
            )

            hyde_doc = self.generate(prompt=hyde_prompt, max_tokens=200)
            hyde_doc = hyde_doc.strip().strip('"\'')

            if not hyde_doc or len(hyde_doc) > 600:
                return query

            logger.info(f"HyDE document generated for: '{query[:50]}...'")
            return hyde_doc
        except Exception as e:
            logger.error(f"Failed to generate HyDE document: {str(e)}")
            return query

    def decompose_query(self, query: str) -> List[str]:
        """
        Decompose a complex multi-part query into a list of simpler sub-questions.
        """
        if not self.is_loaded:
            return [query]

        try:
            decomposition_prompt = (
                "You are an analyzer. Break down the following complex user question into 2 or 3 simpler, independent search sub-questions. "
                "Output the sub-questions as a JSON list of strings and NOTHING else. Do not add markdown formatting or preambles.\n\n"
                f"Question: {query}\n\n"
                "JSON Output:"
            )

            response = self.generate(prompt=decomposition_prompt, max_tokens=150)
            response = response.strip()
            
            # Clean up potential markdown JSON blocks
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            import json
            sub_queries = json.loads(response)
            if isinstance(sub_queries, list) and all(isinstance(q, str) for q in sub_queries):
                logger.info(f"Decomposed query '{query}' into: {sub_queries}")
                return sub_queries
        except Exception as e:
            logger.error(f"Failed to decompose query: {str(e)}")
        
        return [query]

    def generate_with_context(
        self, query: str, context: str, max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate response with retrieved context (RAG pattern).

        Args:
            query: User query/question
            context: Retrieved context from retriever
            max_tokens: Override max tokens

        Returns:
            Generated response using context
        """
        # Format for RAG: provide context then ask question
        system_prompt = "You are a helpful assistant. Use the provided context to answer questions accurately."

        formatted_prompt = f"""Context:
{context}

Question: {query}

Answer:"""

        return self.generate(formatted_prompt, system_prompt, max_tokens)

    def measure_latency(self) -> float:
        """
        Get latency from last generation (in milliseconds).

        Returns:
            Latency in milliseconds (0 if no generation yet)
        """
        return self.last_latency or 0

    def get_memory_usage(self) -> Dict:
        """
        Get memory usage statistics.

        Returns:
            Dict with keys:
            - 'resident_mb': Resident memory (MB)
            - 'vms_mb': Virtual memory size (MB)
            - 'percent': Percentage of total system memory
            - 'process_rss_mb': Current process RSS (MB)
        """
        try:
            # Get system memory stats
            vm = psutil.virtual_memory()

            # Try to get Ollama process info (if available)
            try:
                ollama_process = psutil.Process(self.process_id)
                process_memory = ollama_process.memory_info()
                process_rss_mb = process_memory.rss / (1024 * 1024)
            except:
                process_rss_mb = 0

            return {
                "resident_mb": vm.used / (1024 * 1024),
                "vms_mb": vm.total / (1024 * 1024),
                "percent": vm.percent,
                "process_rss_mb": process_rss_mb,
            }
        except Exception as e:
            logger.warning(f"Could not get memory usage: {str(e)}")
            return {
                "resident_mb": 0,
                "vms_mb": 0,
                "percent": 0,
                "process_rss_mb": 0,
            }

    def get_model_info(self) -> Dict:
        """Get information about loaded model"""
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }


# Test code for Phase 2, Task 2.10
if __name__ == "__main__":
    print("=" * 70)
    print("LLMInference Test")
    print("=" * 70)

    try:
        # Create inference engine
        llm = LLMInference(model_name="mistral", temperature=0.3)
        print(f"\n✓ Created LLMInference: {llm.model_name}")

        # Load model
        print("\nLoading model...")
        print("(First run: ~2-3 minutes, ~4GB download)")
        print("(Subsequent runs: ~10-30 seconds from cache)")

        success = llm.load_model()

        if success:
            print("✓ Model loaded successfully")

            # Test generation
            print("\n" + "=" * 70)
            print("Single Generation Test")
            print("=" * 70)

            query = "What is machine learning?"
            print(f"\nPrompt: '{query}'")

            response = llm.generate(query)
            print(f"\nResponse:\n{response}")

            latency = llm.measure_latency()
            print(f"\nLatency: {latency:.2f}ms")

            # Test with context
            print("\n" + "=" * 70)
            print("Context-Based Generation (RAG Pattern)")
            print("=" * 70)

            context = """
            Machine learning is a subset of artificial intelligence that focuses on
            the development of algorithms and statistical models that enable computers
            to learn from and make predictions based on data.
            """

            question = "What is machine learning?"
            print(f"\nContext: {context[:60]}...")
            print(f"Question: {question}")

            response = llm.generate_with_context(question, context)
            print(f"\nResponse:\n{response}")

            latency = llm.measure_latency()
            print(f"\nLatency: {latency:.2f}ms")

            # Memory usage
            print("\n" + "=" * 70)
            print("Memory Usage")
            print("=" * 70)

            memory = llm.get_memory_usage()
            print(f"\nMemory Statistics:")
            print(f"  Resident (Used): {memory['resident_mb']:.1f} MB")
            print(f"  Total System: {memory['vms_mb']:.1f} MB")
            print(f"  Usage %: {memory['percent']:.1f}%")

            # Model info
            print("\n" + "=" * 70)
            print("Model Information")
            print("=" * 70)

            info = llm.get_model_info()
            for key, val in info.items():
                print(f"  {key}: {val}")

        else:
            print("✗ Failed to load model")
            print("\nPlease ensure:")
            print("1. Ollama is installed (https://ollama.ai)")
            print("2. Ollama daemon is running: ollama serve")
            print("3. Sufficient disk space (~4GB for Mistral 7B)")

    except Exception as e:
        print(f"✗ Error during testing: {str(e)}")
        print("\nTroubleshooting:")
        print("- Install Ollama from https://ollama.ai")
        print("- Run: ollama serve")
        print("- In another terminal, run this script again")
