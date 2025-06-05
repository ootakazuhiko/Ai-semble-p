"""
AI処理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog
from typing import Optional, Dict, Any
import uuid
import time

from config.settings import get_settings
from services.connection_pool import get_connection_pool
from services.model_registry import get_model_registry
from services.auto_model_selector import get_auto_model_selector

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()

class LLMRequest(BaseModel):
    """LLM処理リクエスト"""
    prompt: str
    model: Optional[str] = "auto"
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    priority: Optional[str] = "balanced"  # quality, cost, speed, balanced
    auto_select: Optional[bool] = True

class VisionRequest(BaseModel):
    """画像解析リクエスト"""
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    task: str = "analyze"
    options: Optional[Dict[str, Any]] = {}

class NLPRequest(BaseModel):
    """NLP処理リクエスト"""
    text: str
    task: str = "analyze"
    language: str = "auto"
    options: Optional[Dict[str, Any]] = {}

class LLMResponse(BaseModel):
    """LLM処理レスポンス"""
    job_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    model_used: Optional[str] = None
    selection_reason: Optional[str] = None
    processing_time: Optional[float] = None

class VisionResponse(BaseModel):
    """画像解析レスポンス"""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class NLPResponse(BaseModel):
    """NLP処理レスポンス"""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/llm/completion", response_model=LLMResponse)
async def llm_completion(request: LLMRequest):
    """LLM推論実行 (自動モデル選択対応)"""
    job_id = str(uuid.uuid4())
    
    logger.info(
        "llm_request_received",
        job_id=job_id,
        model=request.model,
        prompt_length=len(request.prompt),
        auto_select=request.auto_select
    )
    
    try:
        start_time = time.time()
        
        # 自動モデル選択
        selected_model = request.model
        selection_reason = "User specified model"
        
        if request.auto_select and (request.model == "auto" or request.model == "default"):
            selector = get_auto_model_selector()
            selection = selector.select_optimal_model(
                request.dict(), 
                task_type="llm",
                priority=request.priority
            )
            selected_model = selection.model_name
            selection_reason = selection.reason
            
            logger.info(
                "auto_model_selected",
                job_id=job_id,
                selected_model=selected_model,
                confidence=selection.confidence,
                reason=selection_reason
            )
        
        # モデル情報を取得
        registry = get_model_registry()
        model_info = registry.get_model_info(selected_model)
        
        if not model_info:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{selected_model}' not found in registry"
            )
        
        # リクエストを更新
        request_data = request.dict()
        request_data["model"] = selected_model
        
        connection_pool = await get_connection_pool()
        
        response = await connection_pool.post(
            f"{settings.llm_service_url}/completion",
            json=request_data
        )
        response.raise_for_status()
        result = response.json()
        
        processing_time = time.time() - start_time
            
        logger.info(
            "llm_request_completed",
            job_id=job_id,
            status="success",
            model_used=selected_model,
            processing_time=processing_time
        )
        
        return LLMResponse(
            job_id=job_id,
            status="completed",
            result=result.get("text", ""),
            model_used=selected_model,
            selection_reason=selection_reason,
            processing_time=processing_time
        )
        
    except Exception as e:
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            logger.error(
                "llm_request_failed",
                job_id=job_id,
                error=str(e),
                status_code=e.response.status_code
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LLM service error: {e}"
            )
        else:
            logger.error(
                "llm_request_error",
                job_id=job_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail=f"Internal error: {e}"
            )

@router.post("/vision/analyze", response_model=VisionResponse)
async def vision_analyze(request: VisionRequest):
    """画像解析実行"""
    job_id = str(uuid.uuid4())
    
    logger.info(
        "vision_request_received",
        job_id=job_id,
        task=request.task,
        image_url=request.image_url
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.vision_service_url}/analyze",
                json=request.dict(),
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            
        logger.info(
            "vision_request_completed",
            job_id=job_id,
            status="success"
        )
        
        return VisionResponse(
            job_id=job_id,
            status="completed",
            result=result
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(
            "vision_request_failed",
            job_id=job_id,
            error=str(e),
            status_code=e.response.status_code
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Vision service error: {e}"
        )
    except Exception as e:
        logger.error(
            "vision_request_error",
            job_id=job_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {e}"
        )

@router.post("/nlp/process", response_model=NLPResponse)
async def nlp_process(request: NLPRequest):
    """NLP処理実行"""
    job_id = str(uuid.uuid4())
    
    logger.info(
        "nlp_request_received",
        job_id=job_id,
        task=request.task,
        text_length=len(request.text)
    )
    
    try:
        start_time = time.time()
        connection_pool = await get_connection_pool()
        
        response = await connection_pool.post(
            f"{settings.nlp_service_url}/process",
            json=request.dict()
        )
        response.raise_for_status()
        result = response.json()
        
        processing_time = time.time() - start_time
            
        logger.info(
            "nlp_request_completed",
            job_id=job_id,
            status="success"
        )
        
        return NLPResponse(
            job_id=job_id,
            status="completed",
            result=result
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(
            "nlp_request_failed",
            job_id=job_id,
            error=str(e),
            status_code=e.response.status_code
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"NLP service error: {e}"
        )
    except Exception as e:
        logger.error(
            "nlp_request_error",
            job_id=job_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {e}"
        )