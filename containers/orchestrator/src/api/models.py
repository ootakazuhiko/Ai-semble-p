"""
モデル管理API
動的なモデル登録・管理・選択機能を提供
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import structlog

from services.model_registry import get_model_registry
from services.auto_model_selector import get_auto_model_selector

logger = structlog.get_logger()
router = APIRouter()

class ModelInfo(BaseModel):
    """モデル情報"""
    provider: str
    model_id: Optional[str] = None
    endpoint: Optional[str] = None
    task: str
    capabilities: List[str]
    quality_score: Optional[float] = None
    speed_score: Optional[float] = None
    cost_per_token: Optional[float] = None
    local: Optional[bool] = False

class ModelRegistrationRequest(BaseModel):
    """モデル登録リクエスト"""
    category: str
    model_name: str
    model_info: ModelInfo

class ModelUpdateRequest(BaseModel):
    """モデル更新リクエスト"""
    updates: Dict[str, Any]

class ModelSelectionRequest(BaseModel):
    """モデル選択リクエスト"""
    prompt: str
    task_type: str = "llm"
    priority: str = "balanced"  # quality, cost, speed, balanced
    max_tokens: Optional[int] = 100
    options: Optional[Dict[str, Any]] = {}

class ModelSelectionResponse(BaseModel):
    """モデル選択レスポンス"""
    selected_model: str
    confidence: float
    reason: str
    fallback_models: List[str]
    model_info: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class ModelListResponse(BaseModel):
    """モデル一覧レスポンス"""
    models: Dict[str, Any]
    total_count: int
    filtered_count: int

class ModelStatsResponse(BaseModel):
    """モデル統計レスポンス"""
    total_models: int
    categories: Dict[str, int]
    providers: Dict[str, int]
    tasks: Dict[str, int]

@router.get("/", response_model=ModelListResponse)
async def list_models(
    task: Optional[str] = Query(None, description="Filter by task type"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """利用可能なモデル一覧を取得"""
    try:
        registry = get_model_registry()
        
        # フィルタリング
        if task or provider:
            models = registry.list_available_models(task=task, provider=provider)
        else:
            models = registry.list_available_models()
        
        # カテゴリフィルタ
        if category and category in models:
            models = {category: models[category]}
        elif category:
            models = {}
        
        # カウント計算
        total_stats = registry.get_model_stats()
        filtered_count = sum(len(cat_models) for cat_models in models.values() if isinstance(cat_models, dict))
        
        logger.info("models_listed",
                   total_count=total_stats["total_models"],
                   filtered_count=filtered_count,
                   filters={"task": task, "provider": provider, "category": category})
        
        return ModelListResponse(
            models=models,
            total_count=total_stats["total_models"],
            filtered_count=filtered_count
        )
        
    except Exception as e:
        logger.error("failed_to_list_models", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")

@router.get("/stats", response_model=ModelStatsResponse)
async def get_model_stats():
    """モデル統計情報を取得"""
    try:
        registry = get_model_registry()
        stats = registry.get_model_stats()
        
        logger.info("model_stats_retrieved", stats=stats)
        
        return ModelStatsResponse(**stats)
        
    except Exception as e:
        logger.error("failed_to_get_stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get model stats: {e}")

@router.get("/{model_name}")
async def get_model_info(model_name: str):
    """特定のモデル情報を取得"""
    try:
        registry = get_model_registry()
        model_info = registry.get_model_info(model_name)
        
        if not model_info:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        logger.info("model_info_retrieved", model_name=model_name)
        
        return {"model_name": model_name, "info": model_info}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_get_model_info", model_name=model_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {e}")

@router.post("/register")
async def register_model(request: ModelRegistrationRequest):
    """新しいモデルを登録"""
    try:
        registry = get_model_registry()
        
        success = registry.register_model(
            category=request.category,
            model_name=request.model_name,
            model_info=request.model_info.dict()
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to register model")
        
        logger.info("model_registered",
                   category=request.category,
                   model_name=request.model_name)
        
        return {
            "status": "success",
            "message": f"Model '{request.model_name}' registered successfully",
            "category": request.category,
            "model_name": request.model_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_register_model",
                    model_name=request.model_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to register model: {e}")

@router.patch("/{model_name}")
async def update_model(model_name: str, request: ModelUpdateRequest):
    """モデル情報を更新"""
    try:
        registry = get_model_registry()
        
        success = registry.update_model(model_name, request.updates)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found or update failed")
        
        logger.info("model_updated",
                   model_name=model_name,
                   updates=list(request.updates.keys()))
        
        return {
            "status": "success",
            "message": f"Model '{model_name}' updated successfully",
            "model_name": model_name,
            "updated_fields": list(request.updates.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_update_model",
                    model_name=model_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update model: {e}")

@router.delete("/{model_name}")
async def delete_model(model_name: str):
    """モデルを削除"""
    try:
        registry = get_model_registry()
        
        success = registry.remove_model(model_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        logger.info("model_deleted", model_name=model_name)
        
        return {
            "status": "success",
            "message": f"Model '{model_name}' deleted successfully",
            "model_name": model_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_delete_model",
                    model_name=model_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {e}")

@router.post("/select", response_model=ModelSelectionResponse)
async def select_model(request: ModelSelectionRequest):
    """最適なモデルを自動選択"""
    try:
        selector = get_auto_model_selector()
        
        # 選択実行
        selection = selector.select_optimal_model(
            request.dict(),
            task_type=request.task_type,
            priority=request.priority
        )
        
        # 詳細説明を取得
        explanation = selector.get_selection_explanation(selection)
        
        logger.info("model_auto_selected",
                   selected_model=selection.model_name,
                   confidence=selection.confidence,
                   task_type=request.task_type,
                   priority=request.priority)
        
        return ModelSelectionResponse(
            selected_model=selection.model_name,
            confidence=selection.confidence,
            reason=selection.reason,
            fallback_models=selection.fallback_models,
            model_info=explanation.get("model_info"),
            performance_metrics=explanation.get("performance_metrics")
        )
        
    except Exception as e:
        logger.error("failed_to_select_model",
                    task_type=request.task_type,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to select model: {e}")

@router.get("/capabilities/{capability}")
async def list_models_by_capability(capability: str):
    """特定の能力を持つモデル一覧"""
    try:
        registry = get_model_registry()
        models = registry.list_models_by_capability(capability)
        
        logger.info("models_by_capability_retrieved",
                   capability=capability,
                   model_count=len(models))
        
        return {
            "capability": capability,
            "models": models,
            "count": len(models)
        }
        
    except Exception as e:
        logger.error("failed_to_list_by_capability",
                    capability=capability,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list models by capability: {e}")

@router.post("/reload")
async def reload_models():
    """モデル設定をリロード"""
    try:
        registry = get_model_registry()
        success = await registry.reload_config()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reload model configuration")
        
        stats = registry.get_model_stats()
        
        logger.info("model_config_reloaded", stats=stats)
        
        return {
            "status": "success",
            "message": "Model configuration reloaded successfully",
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_reload_models", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reload models: {e}")