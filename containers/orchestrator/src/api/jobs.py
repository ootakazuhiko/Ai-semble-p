"""
ジョブ管理API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog
from typing import Dict, Any, Optional
from enum import Enum

logger = structlog.get_logger()

router = APIRouter()

class JobStatus(str, Enum):
    """ジョブステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobResponse(BaseModel):
    """ジョブ情報レスポンス"""
    job_id: str
    status: JobStatus
    created_at: float
    updated_at: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# インメモリジョブストレージ（本番環境では外部ストレージを使用）
job_store: Dict[str, Dict[str, Any]] = {}

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """ジョブ状態取得"""
    logger.info("job_status_requested", job_id=job_id)
    
    if job_id not in job_store:
        logger.warning("job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    job_data = job_store[job_id]
    
    return JobResponse(
        job_id=job_id,
        status=job_data["status"],
        created_at=job_data["created_at"],
        updated_at=job_data["updated_at"],
        result=job_data.get("result"),
        error=job_data.get("error")
    )

@router.get("/")
async def list_jobs():
    """ジョブ一覧取得"""
    logger.info("job_list_requested")
    
    jobs = []
    for job_id, job_data in job_store.items():
        jobs.append(JobResponse(
            job_id=job_id,
            status=job_data["status"],
            created_at=job_data["created_at"],
            updated_at=job_data["updated_at"],
            result=job_data.get("result"),
            error=job_data.get("error")
        ))
    
    return {"jobs": jobs, "total": len(jobs)}

@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """ジョブ削除"""
    logger.info("job_deletion_requested", job_id=job_id)
    
    if job_id not in job_store:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    del job_store[job_id]
    logger.info("job_deleted", job_id=job_id)
    
    return {"message": f"Job {job_id} deleted successfully"}