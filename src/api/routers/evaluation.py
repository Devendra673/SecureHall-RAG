import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..db.models import get_db, User, EvaluationMetric
from ..db.dependencies import require_admin, require_hr_admin
from ..services.rag_engine import get_pipeline
from ..services.evaluation_service import RAGASEvaluator

logger = logging.getLogger("securehall-rag.evaluation")
router = APIRouter()

# --- Request/Response Schemas ---
class SingleEvaluationRequest(BaseModel):
    query: str
    answer: str
    context: str
    ground_truth: Optional[str] = ""

class SingleEvaluationResponse(BaseModel):
    id: str
    query: str
    answer: str
    context: str
    faithfulness_score: Optional[float]
    answer_relevance_score: Optional[float]
    context_recall_score: Optional[float]
    nli_faithfulness_score: Optional[float] = None
    evaluated_at: str


class BatchEntryRequest(BaseModel):
    query: str
    ground_truth: Optional[str] = ""

class BatchEvaluationRequest(BaseModel):
    entries: List[BatchEntryRequest]

class EvaluationHistoryItem(BaseModel):
    id: str
    query: str
    answer: str
    context: str
    faithfulness_score: Optional[float]
    answer_relevance_score: Optional[float]
    context_recall_score: Optional[float]
    nli_faithfulness_score: Optional[float] = None
    evaluated_at: Any

# --- Endpoints ---

@router.post("/run", response_model=SingleEvaluationResponse, dependencies=[Depends(require_hr_admin)])
def run_evaluation(
    body: SingleEvaluationRequest,
    current_user: User = Depends(require_hr_admin),
    db: Session = Depends(get_db)
):
    """
    Run evaluation on a single query, context, and answer.
    Saves results to SQLite and returns scores.
    """
    pipeline = get_pipeline()
    if not pipeline or not pipeline.llm:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM Inference engine is not initialized or loaded."
        )

    evaluator = RAGASEvaluator(pipeline.llm)
    scores = evaluator.evaluate(
        query=body.query,
        answer=body.answer,
        context=body.context,
        ground_truth=body.ground_truth
    )

    metric = EvaluationMetric(
        query=body.query,
        answer=body.answer,
        context=body.context,
        faithfulness_score=scores["faithfulness"],
        answer_relevance_score=scores["answer_relevance"],
        context_recall_score=scores["context_recall"],
        nli_faithfulness_score=scores.get("nli_faithfulness"),
        user_id=current_user.id
    )

    db.add(metric)
    db.commit()
    db.refresh(metric)

    return SingleEvaluationResponse(
        id=metric.id,
        query=metric.query,
        answer=metric.answer,
        context=metric.context,
        faithfulness_score=metric.faithfulness_score,
        answer_relevance_score=metric.answer_relevance_score,
        context_recall_score=metric.context_recall_score,
        nli_faithfulness_score=metric.nli_faithfulness_score,
        evaluated_at=metric.evaluated_at.isoformat()
    )

@router.get("/history", response_model=List[EvaluationHistoryItem], dependencies=[Depends(require_hr_admin)])
def get_evaluation_history(
    db: Session = Depends(get_db)
):
    """
    Fetch all past evaluation results, ordered by timestamp descending.
    """
    metrics = db.query(EvaluationMetric).order_by(EvaluationMetric.evaluated_at.desc()).all()
    return metrics

@router.post("/batch", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])
def run_batch_evaluation(
    body: BatchEvaluationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Run evaluation on a batch of queries.
    Each query is run through the RAG pipeline first to get context and answer,
    then evaluated and saved.
    """
    pipeline = get_pipeline()
    if not pipeline or not pipeline.llm:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG Pipeline or LLM is not initialized."
        )

    evaluator = RAGASEvaluator(pipeline.llm)
    results = []

    for entry in body.entries:
        try:
            rag_res = pipeline.query(question=entry.query)
            answer = rag_res.get("answer", "")
            
            # Reconstruct context from citations
            citations = rag_res.get("citations", [])
            context_text = "\n\n".join(cit[2] for cit in citations) if citations else ""
            
            scores = evaluator.evaluate(
                query=entry.query,
                answer=answer,
                context=context_text,
                ground_truth=entry.ground_truth
            )
            
            metric = EvaluationMetric(
                query=entry.query,
                answer=answer,
                context=context_text,
                faithfulness_score=scores["faithfulness"],
                answer_relevance_score=scores["answer_relevance"],
                context_recall_score=scores["context_recall"],
                nli_faithfulness_score=scores.get("nli_faithfulness"),
                user_id=current_user.id
            )
            
            db.add(metric)
            results.append({
                "query": entry.query,
                "answer": answer,
                "scores": scores
            })
        except Exception as e:
            logger.error(f"Error in batch eval for query '{entry.query}': {e}")
            continue

    db.commit()
    return {"message": f"Successfully evaluated {len(results)} entries.", "results": results}
