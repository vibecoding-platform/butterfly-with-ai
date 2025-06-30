"""
コンテキスト推定API

オペレーションコンテキスト推定機能のREST APIエンドポイント
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from .inference_engine import OperationContextInferenceEngine
from .models import OperationContext
from .pattern_learner import OperationPatternLearner

logger = logging.getLogger(__name__)

# API Router
router = APIRouter(prefix="/api/context", tags=["Operation Context"])

# Global instances (initialized at startup)
inference_engine: Optional[OperationContextInferenceEngine] = None
pattern_learner: Optional[OperationPatternLearner] = None


# Pydantic Models for API
class OperationContextResponse(BaseModel):
    """オペレーションコンテキストレスポンス"""

    terminal_id: str
    operation_type: str
    stage: str
    confidence: float
    start_time: str
    progress_percentage: float
    estimated_duration: Optional[float] = None
    command_sequence: List[str] = Field(default_factory=list)
    next_likely_commands: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)


class InferenceResultResponse(BaseModel):
    """推定結果レスポンス"""

    terminal_id: str
    timestamp: str
    primary_context: OperationContextResponse
    overall_confidence: float
    reasoning: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PatternLearningRequest(BaseModel):
    """パターン学習リクエスト"""

    days: int = Field(30, ge=1, le=365, description="Learning period in days")
    retrain: bool = Field(False, description="Whether to retrain existing patterns")


class PatternLearningResponse(BaseModel):
    """パターン学習レスポンス"""

    status: str
    patterns_learned: int
    learning_duration: float
    message: str


# API Endpoints


@router.get("/infer/{terminal_id}", response_model=InferenceResultResponse)
async def infer_operation_context(
    terminal_id: str = Path(description="Terminal ID to analyze"),
) -> InferenceResultResponse:
    """
    指定ターミナルの現在のオペレーションコンテキストを推定
    """
    if not inference_engine:
        raise HTTPException(status_code=503, detail="Context inference engine not initialized")

    try:
        result = await inference_engine.infer_current_operation(terminal_id)

        return InferenceResultResponse(
            terminal_id=result.terminal_id,
            timestamp=result.timestamp.isoformat(),
            primary_context=_context_to_response(result.primary_context),
            overall_confidence=result.overall_confidence,
            reasoning=result.reasoning,
            recommendations=result.recommendations,
            warnings=result.warnings,
        )

    except Exception as e:
        logger.error(f"Failed to infer context for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Context inference failed: {e!s}")


@router.get("/status/{terminal_id}", response_model=OperationContextResponse)
async def get_operation_status(
    terminal_id: str = Path(description="Terminal ID to check"),
) -> OperationContextResponse:
    """
    指定ターミナルの現在のオペレーション状態を取得
    """
    if not inference_engine:
        raise HTTPException(status_code=503, detail="Context inference engine not initialized")

    try:
        # アクティブなコンテキストを確認
        active_context = inference_engine.active_contexts.get(terminal_id)

        if not active_context:
            # 新しい推定を実行
            result = await inference_engine.infer_current_operation(terminal_id)
            active_context = result.primary_context

        return _context_to_response(active_context)

    except Exception as e:
        logger.error(f"Failed to get status for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {e!s}")


@router.get("/predict/{terminal_id}/next-commands")
async def predict_next_commands(
    terminal_id: str = Path(description="Terminal ID to predict for"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of predictions"),
) -> Dict[str, List[str]]:
    """
    指定ターミナルの次に実行される可能性の高いコマンドを予測
    """
    if not inference_engine:
        raise HTTPException(status_code=503, detail="Context inference engine not initialized")

    try:
        # 現在のコンテキストを取得
        active_context = inference_engine.active_contexts.get(terminal_id)

        if not active_context:
            # コンテキストが無い場合は推定を実行
            result = await inference_engine.infer_current_operation(terminal_id)
            active_context = result.primary_context

        return {
            "next_commands": active_context.next_likely_commands[:limit],
            "confidence": active_context.confidence,
            "operation_type": active_context.operation_type.value,
        }

    except Exception as e:
        logger.error(f"Failed to predict commands for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Command prediction failed: {e!s}")


@router.get("/active-operations")
async def get_active_operations() -> Dict[str, List[OperationContextResponse]]:
    """
    現在アクティブな全オペレーションを取得
    """
    if not inference_engine:
        raise HTTPException(status_code=503, detail="Context inference engine not initialized")

    try:
        active_operations = []

        for terminal_id, context in inference_engine.active_contexts.items():
            active_operations.append(_context_to_response(context))

        return {"active_operations": active_operations, "count": len(active_operations)}

    except Exception as e:
        logger.error(f"Failed to get active operations: {e}")
        raise HTTPException(status_code=500, detail=f"Active operations retrieval failed: {e!s}")


@router.post("/learn-patterns", response_model=PatternLearningResponse)
async def learn_operation_patterns(request: PatternLearningRequest) -> PatternLearningResponse:
    """
    過去のコマンド履歴からオペレーションパターンを学習
    """
    if not pattern_learner:
        raise HTTPException(status_code=503, detail="Pattern learner not initialized")

    try:
        start_time = datetime.utcnow()

        # パターン学習を実行
        learned_patterns = await pattern_learner.learn_patterns_from_history(days=request.days)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return PatternLearningResponse(
            status="success",
            patterns_learned=len(learned_patterns),
            learning_duration=duration,
            message=f"Successfully learned {len(learned_patterns)} patterns from {request.days} days of history",
        )

    except Exception as e:
        logger.error(f"Failed to learn patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern learning failed: {e!s}")


@router.get("/patterns/summary")
async def get_patterns_summary() -> Dict[str, Any]:
    """
    学習済みパターンのサマリーを取得
    """
    try:
        # VectorDBから学習済みパターンの統計を取得
        # 実装は簡略化
        summary = {
            "total_patterns": 0,
            "patterns_by_type": {},
            "last_learning_time": None,
            "coverage_percentage": 0.0,
        }

        return summary

    except Exception as e:
        logger.error(f"Failed to get patterns summary: {e}")
        raise HTTPException(status_code=500, detail=f"Patterns summary failed: {e!s}")


@router.get("/analytics/{terminal_id}")
async def get_operation_analytics(
    terminal_id: str = Path(description="Terminal ID to analyze"),
    days: int = Query(7, ge=1, le=30, description="Analysis period in days"),
) -> Dict[str, Any]:
    """
    指定ターミナルのオペレーション分析を取得
    """
    try:
        # オペレーション履歴の分析
        analytics = {
            "terminal_id": terminal_id,
            "analysis_period_days": days,
            "operation_counts": {},
            "average_durations": {},
            "success_rates": {},
            "most_common_operations": [],
            "efficiency_trends": [],
            "recommendations": [],
        }

        # 実際の分析実装はここに追加

        return analytics

    except Exception as e:
        logger.error(f"Failed to get analytics for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics retrieval failed: {e!s}")


@router.post("/feedback/{terminal_id}")
async def submit_context_feedback(
    feedback: Dict[str, Any], terminal_id: str = Path(description="Terminal ID")
) -> Dict[str, str]:
    """
    コンテキスト推定結果に対するフィードバックを送信
    （将来の改善に使用）
    """
    try:
        # フィードバックを保存（実装は簡略化）
        logger.info(f"Received feedback for terminal {terminal_id}: {feedback}")

        return {
            "status": "success",
            "message": "Feedback received and will be used to improve context inference",
        }

    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {e!s}")


# Helper Functions


def _context_to_response(context: OperationContext) -> OperationContextResponse:
    """OperationContextをレスポンスモデルに変換"""
    return OperationContextResponse(
        terminal_id=context.terminal_id,
        operation_type=context.operation_type.value,
        stage=context.stage.value,
        confidence=context.confidence,
        start_time=context.start_time.isoformat(),
        progress_percentage=context.progress_percentage,
        estimated_duration=context.estimated_duration,
        command_sequence=context.command_sequence,
        next_likely_commands=context.next_likely_commands,
        risk_factors=context.risk_factors,
        suggested_actions=context.suggested_actions,
    )


# Initialization Functions


def initialize_context_inference(
    vector_storage, sql_storage
) -> Tuple[OperationContextInferenceEngine, OperationPatternLearner]:
    """
    コンテキスト推定エンジンを初期化
    """
    global inference_engine, pattern_learner

    try:
        pattern_learner = OperationPatternLearner(vector_storage, sql_storage)
        inference_engine = OperationContextInferenceEngine(
            vector_storage, sql_storage, pattern_learner
        )

        logger.info("Context inference system initialized successfully")
        return inference_engine, pattern_learner

    except Exception as e:
        logger.error(f"Failed to initialize context inference: {e}")
        raise


async def startup_context_inference():
    """
    起動時のコンテキスト推定システム初期化
    """
    try:
        # 必要に応じて初期パターン学習を実行
        if pattern_learner:
            logger.info("Starting initial pattern learning...")
            await pattern_learner.learn_patterns_from_history(days=7)
            logger.info("Initial pattern learning completed")

    except Exception as e:
        logger.warning(f"Initial pattern learning failed: {e}")


# Health Check
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """ヘルスチェック"""
    status = "healthy" if inference_engine and pattern_learner else "unhealthy"

    return {
        "status": status,
        "service": "context-inference",
        "timestamp": datetime.utcnow().isoformat(),
    }
