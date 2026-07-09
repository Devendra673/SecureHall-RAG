"""
Embedding Model Fine-tuning
Phase 12: Academic Features

Implements contrastive fine-tuning of sentence transformer embedding models
using MultipleNegativesRankingLoss on domain-specific Q&A pairs.
"""

import os
import logging
import time
from typing import List, Dict, Any
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from torch.utils.data import DataLoader
    _TRAINING_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    InputExample = None
    losses = None
    DataLoader = None
    _TRAINING_AVAILABLE = False

logger = logging.getLogger(__name__)

class EmbeddingFineTuner:
    def __init__(
        self, 
        base_model: str = "sentence-transformers/all-mpnet-base-v2",
        output_dir: str = "models/finetuned-embeddings"
    ):
        self.base_model = base_model
        self.output_dir = output_dir

    def prepare_training_data(self, qa_pairs: List[Dict[str, str]]) -> List[Any]:
        """
        Convert raw QA pairs into SentenceTransformer InputExamples.
        Each QA pair must have 'question' (query) and 'positive' (matching document chunk).
        """
        if not _TRAINING_AVAILABLE:
            raise RuntimeError("sentence-transformers dependencies not available.")

        examples = []
        for i, pair in enumerate(qa_pairs):
            question = pair.get("question", "").strip()
            positive = pair.get("positive", "").strip()

            if not question or not positive:
                logger.warning(f"Skipping empty pair at index {i}")
                continue

            # InputExample expects list of texts that are semantically close
            examples.append(InputExample(texts=[question, positive]))

        logger.info(f"Prepared {len(examples)} training examples.")
        return examples

    def train(
        self, 
        training_examples: List[Any], 
        epochs: int = 3, 
        batch_size: int = 16, 
        warmup_steps: int = 100
    ) -> str:
        """
        Run contrastive fine-tuning.
        """
        if not _TRAINING_AVAILABLE:
            raise RuntimeError("sentence-transformers or torch packages not available.")

        if not training_examples:
            raise ValueError("No training examples provided.")

        logger.info(f"Initializing base model: {self.base_model}")
        model = SentenceTransformer(self.base_model)

        # Create DataLoader
        train_dataloader = DataLoader(training_examples, shuffle=True, batch_size=batch_size)

        # MultipleNegativesRankingLoss treats other positive matches in the same batch
        # as negative examples. This is ideal for QA retrieval.
        train_loss = losses.MultipleNegativesRankingLoss(model=model)

        logger.info(f"Starting training on {len(training_examples)} examples for {epochs} epochs...")
        start_time = time.time()

        os.makedirs(self.output_dir, exist_ok=True)

        model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            show_progress_bar=False
        )

        elapsed = time.time() - start_time
        logger.info(f"Training completed in {elapsed:.2f} seconds.")

        # Save model
        model.save(self.output_dir)
        logger.info(f"Fine-tuned model saved to {self.output_dir}")

        return self.output_dir
