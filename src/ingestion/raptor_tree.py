import logging
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

logger = logging.getLogger("securehall-rag.raptor")

class RaptorTreeBuilder:
    """
    Builds RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) summary nodes.
    
    Flow:
    1. Cluster raw chunks using KMeans on their embeddings.
    2. Generate cluster-level summaries via the local LLM.
    3. Register summaries as new indexable nodes in the corpus.
    """
    def __init__(self, llm, dense_retriever, num_clusters: int = 3, max_iterations: int = 15):
        self.llm = llm
        self.dense_retriever = dense_retriever
        self.num_clusters = num_clusters
        self.max_iterations = max_iterations

    def kmeans_clustering(self, embeddings: np.ndarray, k: int) -> List[List[int]]:
        """
        K-Means clustering on embeddings using cosine similarity.
        Returns a list of cluster lists containing item indices.
        """
        n_samples = embeddings.shape[0]
        if n_samples <= k:
            return [[i] for i in range(n_samples)]

        # L2 normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1.0, norms)
        normalized_embeddings = embeddings / norms

        # Randomly initialize centroids
        indices = np.random.choice(n_samples, k, replace=False)
        centroids = normalized_embeddings[indices]

        labels = np.zeros(n_samples, dtype=int)

        for _ in range(self.max_iterations):
            # Calculate similarity matrix
            similarities = np.dot(normalized_embeddings, centroids.T)  # (n_samples, k)
            new_labels = np.argmax(similarities, axis=1)

            if np.array_equal(labels, new_labels):
                break
            labels = new_labels

            # Update centroids
            for i in range(k):
                cluster_points = normalized_embeddings[labels == i]
                if cluster_points.shape[0] > 0:
                    center = np.mean(cluster_points, axis=0)
                    center_norm = np.linalg.norm(center)
                    centroids[i] = center / center_norm if center_norm > 0 else center

        clusters = [[] for _ in range(k)]
        for idx, label in enumerate(labels):
            clusters[label].append(idx)
        
        # Filter empty clusters
        return [c for c in clusters if c]

    def build_summaries(self, texts: List[str], chunk_ids: List[str]) -> Tuple[List[str], List[str], List[dict]]:
        """
        Clusters texts, generates summaries for clusters, and returns new summary texts and IDs.
        """
        if not self.llm or not self.llm.is_loaded or len(texts) < 3:
            logger.info("Skipping RAPTOR summaries (LLM not loaded or corpus too small)")
            return [], [], []

        try:
            logger.info(f"RAPTOR: Generating embeddings for clustering {len(texts)} chunks...")
            # Generate embeddings
            embeddings = np.array(self.dense_retriever.embed_texts(texts))
            
            # Select reasonable K based on corpus size
            k = max(2, min(self.num_clusters, len(texts) // 2))
            logger.info(f"RAPTOR: Clustering chunks into {k} clusters...")
            
            clusters = self.kmeans_clustering(embeddings, k)
            
            summary_texts = []
            summary_ids = []
            summary_metadata = []
            
            for cluster_idx, cluster in enumerate(clusters):
                cluster_texts = [texts[idx] for idx in cluster]
                cluster_chunk_ids = [chunk_ids[idx] for idx in cluster]
                
                # Build summary prompt
                context_to_summarize = "\n---\n".join(cluster_texts[:5]) # limit to first 5 chunks to save context length
                prompt = (
                    "You are a fact-based abstractive summarizer. Synthesize the key topics, rules, and facts from the text sections below "
                    "into a single concise paragraph (2-3 sentences max) that summarizes the core policies/guidelines. "
                    "Output ONLY the summary text. Do not preface it.\n\n"
                    f"Text Sections:\n{context_to_summarize}\n\n"
                    "Summary:"
                )
                
                logger.info(f"RAPTOR: Summarizing cluster {cluster_idx + 1}/{k} containing {len(cluster_texts)} chunks...")
                summary = self.llm.generate(prompt=prompt, max_tokens=250)
                summary = summary.strip().strip('"\'')
                
                if summary and len(summary) > 20:
                    summary_text = f"Executive Summary (High-Level Topic Overview):\n{summary}"
                    # Assign raptor doc summary chunk id
                    doc_prefix = cluster_chunk_ids[0].split("_")[0] if "_" in cluster_chunk_ids[0] else "doc"
                    summary_id = f"raptor_summary_{doc_prefix}_{cluster_idx:04d}"
                    
                    summary_texts.append(summary_text)
                    summary_ids.append(summary_id)
                    summary_metadata.append({
                        "chunk_id": summary_id,
                        "children_ids": cluster_chunk_ids,
                    })
                    logger.info(f"RAPTOR: Summary generated: '{summary_text[:60]}...'")
            
            return summary_texts, summary_ids, summary_metadata
        except Exception as e:
            logger.error(f"Failed to build RAPTOR summary tree: {e}")
            return [], [], []
