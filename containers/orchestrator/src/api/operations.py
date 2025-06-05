"""
本番運用管理API
監視・ログ・バックアップ機能の統合管理インターフェース
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog

from services.monitoring import get_monitoring_service
from services.logging_service import get_logging_service, LogFilter, LogEntry
from services.backup_service import get_backup_service, BackupJob

logger = structlog.get_logger()
router = APIRouter()

# リクエスト・レスポンスモデル
class SystemStatusResponse(BaseModel):
    """システム状況レスポンス"""
    timestamp: str
    overall_status: str
    services: Dict[str, Any]
    system_metrics: Dict[str, Any]
    recent_alerts: List[Dict[str, Any]]

class LogSearchRequest(BaseModel):
    """ログ検索リクエスト"""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    level: Optional[str] = None
    service: Optional[str] = None
    message_contains: Optional[str] = None
    trace_id: Optional[str] = None
    limit: int = 100

class LogSearchResponse(BaseModel):
    """ログ検索レスポンス"""
    logs: List[Dict[str, Any]]
    total_found: int
    search_params: Dict[str, Any]

class BackupJobRequest(BaseModel):
    """バックアップジョブリクエスト"""
    name: str
    source_paths: List[str]
    destination: str
    schedule: str
    retention_days: int = 7
    compression: bool = True
    enabled: bool = True

class ManualBackupRequest(BaseModel):
    """手動バックアップリクエスト"""
    name: str
    source_paths: List[str]
    compression: bool = True

class AuditLogRequest(BaseModel):
    """監査ログリクエスト"""
    action: str
    user_id: str
    resource: str
    details: Dict[str, Any]
    success: bool = True

# 監視エンドポイント
@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """システム全体の状況取得"""
    try:
        monitoring = get_monitoring_service()
        status = monitoring.get_system_status()
        
        return SystemStatusResponse(**status)
        
    except Exception as e:
        logger.error("failed_to_get_system_status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")

@router.post("/monitoring/start")
async def start_monitoring():
    """監視サービス開始"""
    try:
        monitoring = get_monitoring_service()
        await monitoring.start_monitoring()
        
        return {"status": "success", "message": "Monitoring started"}
        
    except Exception as e:
        logger.error("failed_to_start_monitoring", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {e}")

@router.post("/monitoring/stop")
async def stop_monitoring():
    """監視サービス停止"""
    try:
        monitoring = get_monitoring_service()
        await monitoring.stop_monitoring()
        
        return {"status": "success", "message": "Monitoring stopped"}
        
    except Exception as e:
        logger.error("failed_to_stop_monitoring", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {e}")

@router.post("/monitoring/services")
async def add_monitoring_service(
    name: str = Query(..., description="Service name"),
    url: str = Query(..., description="Health check URL")
):
    """監視対象サービス追加"""
    try:
        monitoring = get_monitoring_service()
        success = monitoring.add_service(name, url)
        
        if success:
            return {"status": "success", "message": f"Service '{name}' added to monitoring"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add service")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_add_monitoring_service", name=name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to add monitoring service: {e}")

@router.delete("/monitoring/services/{service_name}")
async def remove_monitoring_service(service_name: str):
    """監視対象サービス削除"""
    try:
        monitoring = get_monitoring_service()
        success = monitoring.remove_service(service_name)
        
        if success:
            return {"status": "success", "message": f"Service '{service_name}' removed from monitoring"}
        else:
            raise HTTPException(status_code=404, detail="Service not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_remove_monitoring_service", service=service_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to remove monitoring service: {e}")

# ログ管理エンドポイント
@router.post("/logs/search", response_model=LogSearchResponse)
async def search_logs(request: LogSearchRequest):
    """ログ検索"""
    try:
        logging_service = get_logging_service()
        
        # 検索条件を構築
        filter_conditions = LogFilter(
            start_time=datetime.fromisoformat(request.start_time) if request.start_time else None,
            end_time=datetime.fromisoformat(request.end_time) if request.end_time else None,
            level=request.level,
            service=request.service,
            message_contains=request.message_contains,
            trace_id=request.trace_id,
            limit=request.limit
        )
        
        logs = await logging_service.search_logs(filter_conditions)
        
        return LogSearchResponse(
            logs=logs,
            total_found=len(logs),
            search_params=request.dict()
        )
        
    except Exception as e:
        logger.error("failed_to_search_logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search logs: {e}")

@router.get("/logs/stats")
async def get_log_stats(hours: int = Query(24, description="Hours to analyze")):
    """ログ統計取得"""
    try:
        logging_service = get_logging_service()
        stats = await logging_service.get_log_stats(hours)
        
        return stats
        
    except Exception as e:
        logger.error("failed_to_get_log_stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get log stats: {e}")

@router.post("/logs/export")
async def export_logs(
    request: LogSearchRequest,
    format: str = Query("json", description="Export format: json or csv")
):
    """ログエクスポート"""
    try:
        logging_service = get_logging_service()
        
        filter_conditions = LogFilter(
            start_time=datetime.fromisoformat(request.start_time) if request.start_time else None,
            end_time=datetime.fromisoformat(request.end_time) if request.end_time else None,
            level=request.level,
            service=request.service,
            message_contains=request.message_contains,
            trace_id=request.trace_id,
            limit=request.limit
        )
        
        exported_data = await logging_service.export_logs(filter_conditions, format)
        
        return {
            "format": format,
            "data": exported_data,
            "export_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("failed_to_export_logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to export logs: {e}")

@router.post("/logs/audit")
async def create_audit_log(request: AuditLogRequest):
    """監査ログ作成"""
    try:
        logging_service = get_logging_service()
        
        await logging_service.audit_log(
            action=request.action,
            user_id=request.user_id,
            resource=request.resource,
            details=request.details,
            success=request.success
        )
        
        return {"status": "success", "message": "Audit log created"}
        
    except Exception as e:
        logger.error("failed_to_create_audit_log", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create audit log: {e}")

@router.post("/logs/cleanup")
async def cleanup_logs():
    """古いログのクリーンアップ"""
    try:
        logging_service = get_logging_service()
        deleted_files = await logging_service.cleanup_old_logs()
        
        return {
            "status": "success",
            "message": f"Cleaned up {len(deleted_files)} old log files",
            "deleted_files": deleted_files
        }
        
    except Exception as e:
        logger.error("failed_to_cleanup_logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cleanup logs: {e}")

# バックアップ管理エンドポイント
@router.get("/backups/status")
async def get_backup_status():
    """バックアップ状況取得"""
    try:
        backup_service = get_backup_service()
        status = backup_service.get_backup_status()
        
        return status
        
    except Exception as e:
        logger.error("failed_to_get_backup_status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get backup status: {e}")

@router.get("/backups/files")
async def list_backup_files(job_name: Optional[str] = Query(None, description="Filter by job name")):
    """バックアップファイル一覧"""
    try:
        backup_service = get_backup_service()
        files = backup_service.list_backup_files(job_name)
        
        return {
            "backup_files": files,
            "total_count": len(files),
            "filtered_by_job": job_name
        }
        
    except Exception as e:
        logger.error("failed_to_list_backup_files", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list backup files: {e}")

@router.post("/backups/jobs")
async def create_backup_job(request: BackupJobRequest):
    """バックアップジョブ作成"""
    try:
        backup_service = get_backup_service()
        
        job = BackupJob(
            name=request.name,
            source_paths=request.source_paths,
            destination=request.destination,
            schedule=request.schedule,
            retention_days=request.retention_days,
            compression=request.compression,
            enabled=request.enabled
        )
        
        success = backup_service.add_backup_job(job)
        
        if success:
            return {"status": "success", "message": f"Backup job '{request.name}' created"}
        else:
            raise HTTPException(status_code=400, detail="Failed to create backup job")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_create_backup_job", job=request.name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create backup job: {e}")

@router.patch("/backups/jobs/{job_name}")
async def update_backup_job(job_name: str, updates: Dict[str, Any]):
    """バックアップジョブ更新"""
    try:
        backup_service = get_backup_service()
        success = backup_service.update_backup_job(job_name, updates)
        
        if success:
            return {"status": "success", "message": f"Backup job '{job_name}' updated"}
        else:
            raise HTTPException(status_code=404, detail="Backup job not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_update_backup_job", job=job_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update backup job: {e}")

@router.delete("/backups/jobs/{job_name}")
async def delete_backup_job(job_name: str):
    """バックアップジョブ削除"""
    try:
        backup_service = get_backup_service()
        success = backup_service.remove_backup_job(job_name)
        
        if success:
            return {"status": "success", "message": f"Backup job '{job_name}' deleted"}
        else:
            raise HTTPException(status_code=404, detail="Backup job not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_delete_backup_job", job=job_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete backup job: {e}")

@router.post("/backups/jobs/{job_name}/run")
async def run_backup_job(job_name: str, background_tasks: BackgroundTasks):
    """バックアップジョブ手動実行"""
    try:
        backup_service = get_backup_service()
        
        # バックグラウンドでジョブを実行
        background_tasks.add_task(backup_service.run_backup_job, job_name)
        
        return {"status": "success", "message": f"Backup job '{job_name}' started"}
        
    except Exception as e:
        logger.error("failed_to_run_backup_job", job=job_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to run backup job: {e}")

@router.post("/backups/manual")
async def create_manual_backup(request: ManualBackupRequest, background_tasks: BackgroundTasks):
    """手動バックアップ作成"""
    try:
        backup_service = get_backup_service()
        
        # バックグラウンドでバックアップを実行
        background_tasks.add_task(
            backup_service.create_manual_backup,
            request.name,
            request.source_paths,
            request.compression
        )
        
        return {"status": "success", "message": f"Manual backup '{request.name}' started"}
        
    except Exception as e:
        logger.error("failed_to_create_manual_backup", name=request.name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create manual backup: {e}")

@router.post("/backups/restore")
async def restore_backup(
    backup_path: str = Query(..., description="Path to backup file"),
    destination: str = Query("/", description="Restore destination")
):
    """バックアップから復元"""
    try:
        backup_service = get_backup_service()
        success = await backup_service.restore_from_backup(backup_path, destination)
        
        if success:
            return {"status": "success", "message": "Backup restored successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to restore backup")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("failed_to_restore_backup", 
                    backup_path=backup_path, 
                    destination=destination, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {e}")

@router.post("/backups/scheduler/start")
async def start_backup_scheduler():
    """バックアップスケジューラー開始"""
    try:
        backup_service = get_backup_service()
        await backup_service.start_scheduler()
        
        return {"status": "success", "message": "Backup scheduler started"}
        
    except Exception as e:
        logger.error("failed_to_start_backup_scheduler", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start backup scheduler: {e}")

@router.post("/backups/scheduler/stop")
async def stop_backup_scheduler():
    """バックアップスケジューラー停止"""
    try:
        backup_service = get_backup_service()
        await backup_service.stop_scheduler()
        
        return {"status": "success", "message": "Backup scheduler stopped"}
        
    except Exception as e:
        logger.error("failed_to_stop_backup_scheduler", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop backup scheduler: {e}")

# 統合運用エンドポイント
@router.get("/health/comprehensive")
async def comprehensive_health_check():
    """包括的ヘルスチェック"""
    try:
        monitoring = get_monitoring_service()
        logging_service = get_logging_service()
        backup_service = get_backup_service()
        
        # 各サービスの状況を収集
        system_status = monitoring.get_system_status()
        log_stats = await logging_service.get_log_stats(1)  # 過去1時間
        backup_status = backup_service.get_backup_status()
        
        # 総合評価
        overall_health = "healthy"
        issues = []
        
        # システム状況チェック
        if system_status["overall_status"] != "healthy":
            overall_health = "degraded"
            issues.append("System services are not fully healthy")
        
        # エラー率チェック
        error_rate = log_stats.get("error_rate", 0)
        if error_rate > 5:
            overall_health = "degraded"
            issues.append(f"High error rate: {error_rate:.1f}%")
        
        # バックアップ状況チェック
        if not backup_status["scheduler_running"]:
            issues.append("Backup scheduler is not running")
        
        return {
            "overall_health": overall_health,
            "timestamp": datetime.now().isoformat(),
            "issues": issues,
            "system_status": system_status,
            "log_stats": log_stats,
            "backup_status": backup_status
        }
        
    except Exception as e:
        logger.error("failed_comprehensive_health_check", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to perform comprehensive health check: {e}")

@router.post("/maintenance/mode")
async def toggle_maintenance_mode(enable: bool = Query(..., description="Enable/disable maintenance mode")):
    """メンテナンスモード切り替え"""
    try:
        # メンテナンスモードの実装（将来の拡張ポイント）
        # 実際の実装では、リクエストルーティングを制御したり、
        # サービスの一時停止などを行う
        
        status = "enabled" if enable else "disabled"
        
        logger.info("maintenance_mode_toggled", enabled=enable)
        
        return {
            "status": "success",
            "message": f"Maintenance mode {status}",
            "maintenance_mode": enable,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("failed_to_toggle_maintenance_mode", enable=enable, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to toggle maintenance mode: {e}")