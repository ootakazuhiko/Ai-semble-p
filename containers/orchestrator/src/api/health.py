"""
ヘルスチェックAPI
"""
from fastapi import APIRouter
from pydantic import BaseModel
import time
import structlog

logger = structlog.get_logger()

router = APIRouter()

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    timestamp: float
    service: str
    version: str

@router.get("/", response_model=HealthResponse)
async def health_check():
    """ヘルスチェックエンドポイント"""
    logger.info("health_check_requested", service="orchestrator")
    
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        service="orchestrator",
        version="2.0.0"
    )

@router.get("/ready")
async def readiness_check():
    """レディネスチェックエンドポイント"""
    # 依存サービスの状態確認をここで実装
    logger.info("readiness_check_requested", service="orchestrator")
    
    return {"status": "ready", "timestamp": time.time()}

@router.get("/live")
async def liveness_check():
    """ライブネスチェックエンドポイント"""
    logger.info("liveness_check_requested", service="orchestrator")
    
    return {"status": "alive", "timestamp": time.time()}