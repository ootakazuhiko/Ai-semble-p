"""
AI処理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import structlog
from typing import Optional, Dict, Any
import uuid

from ..config.settings import get_settings

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()

class LLMRequest(BaseModel):
    """LLM処理リクエスト"""
    prompt: str
    model: Optional[str] = "default"
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7

class VisionRequest(BaseModel):
    """画像解析リクエスト"""
    image_url: str
    task: str = "analyze"
    options: Optional[Dict[str, Any]] = {}

class LLMResponse(BaseModel):
    """LLM処理レスポンス"""
    job_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None

class VisionResponse(BaseModel):
    """画像解析レスポンス"""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/llm/completion", response_model=LLMResponse)
async def llm_completion(request: LLMRequest):
    """LLM推論実行"""
    job_id = str(uuid.uuid4())
    
    logger.info(
        "llm_request_received",
        job_id=job_id,
        model=request.model,
        prompt_length=len(request.prompt)
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.llm_service_url}/completion",
                json=request.dict(),
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            
        logger.info(
            "llm_request_completed",
            job_id=job_id,
            status="success"
        )
        
        return LLMResponse(
            job_id=job_id,
            status="completed",
            result=result.get("text", "")
        )
        
    except httpx.HTTPStatusError as e:
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
    except Exception as e:
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