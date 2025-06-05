"""
包括的バックアップ・復元サービス
データベース、設定ファイル、ログ、モデルデータの自動バックアップ
"""
import os
import shutil
import tarfile
import gzip
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import structlog
import aiofiles
import yaml
from croniter import croniter

logger = structlog.get_logger()

@dataclass
class BackupJob:
    """バックアップジョブ定義"""
    name: str
    source_paths: List[str]
    destination: str
    schedule: str  # cron形式
    retention_days: int = 7
    compression: bool = True
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

@dataclass
class BackupResult:
    """バックアップ結果"""
    job_name: str
    start_time: datetime
    end_time: datetime
    success: bool
    backup_path: str
    file_size: int
    files_backed_up: int
    error_message: Optional[str] = None

class BackupService:
    """包括的バックアップサービス"""
    
    def __init__(self, backup_root: str = "/var/backups/aisemble"):
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        self.jobs: Dict[str, BackupJob] = {}
        self.backup_history: List[BackupResult] = []
        self.scheduler_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # デフォルトジョブ設定
        self._setup_default_jobs()
        
        logger.info("backup_service_initialized", backup_root=str(self.backup_root))
    
    def _setup_default_jobs(self):
        """デフォルトバックアップジョブ設定"""
        default_jobs = [
            BackupJob(
                name="system_config",
                source_paths=[
                    "/config",
                    "/configs", 
                    "/pods",
                    "/quadlets"
                ],
                destination="config",
                schedule="0 2 * * *",  # 毎日2時
                retention_days=30
            ),
            BackupJob(
                name="logs",
                source_paths=[
                    "/var/log/aisemble",
                    "/var/log/pods"
                ],
                destination="logs",
                schedule="0 3 * * *",  # 毎日3時
                retention_days=7
            ),
            BackupJob(
                name="models",
                source_paths=[
                    "/models",
                    "/var/lib/aisemble/models"
                ],
                destination="models",
                schedule="0 1 * * 0",  # 毎週日曜1時
                retention_days=14
            ),
            BackupJob(
                name="data",
                source_paths=[
                    "/var/lib/aisemble/data",
                    "/data"
                ],
                destination="data",
                schedule="0 4 * * *",  # 毎日4時
                retention_days=14
            )
        ]
        
        for job in default_jobs:
            self.jobs[job.name] = job
            self._calculate_next_run(job)
    
    def _calculate_next_run(self, job: BackupJob):
        """次回実行時間を計算"""
        try:
            cron = croniter(job.schedule, datetime.now())
            job.next_run = cron.get_next(datetime)
        except Exception as e:
            logger.error("failed_to_calculate_next_run", 
                        job=job.name, schedule=job.schedule, error=str(e))
    
    async def start_scheduler(self):
        """バックアップスケジューラー開始"""
        if self.scheduler_running:
            logger.warning("backup_scheduler_already_running")
            return
        
        self.scheduler_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("backup_scheduler_started")
    
    async def stop_scheduler(self):
        """バックアップスケジューラー停止"""
        self.scheduler_running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("backup_scheduler_stopped")
    
    async def _scheduler_loop(self):
        """スケジューラーメインループ"""
        while self.scheduler_running:
            try:
                current_time = datetime.now()
                
                for job in self.jobs.values():
                    if (job.enabled and job.next_run and 
                        current_time >= job.next_run):
                        
                        logger.info("scheduled_backup_starting", job=job.name)
                        await self.run_backup_job(job.name)
                        
                        # 次回実行時間を再計算
                        self._calculate_next_run(job)
                
                # 古いバックアップのクリーンアップ
                await self._cleanup_old_backups()
                
                # 60秒間隔でチェック
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error("backup_scheduler_error", error=str(e))
                await asyncio.sleep(300)  # エラー時は5分待機
    
    async def run_backup_job(self, job_name: str) -> BackupResult:
        """バックアップジョブ実行"""
        if job_name not in self.jobs:
            raise ValueError(f"Backup job '{job_name}' not found")
        
        job = self.jobs[job_name]
        start_time = datetime.now()
        
        logger.info("backup_job_started", job=job_name, start_time=start_time.isoformat())
        
        try:
            # バックアップファイル名生成
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{job_name}_{timestamp}"
            
            if job.compression:
                backup_filename += ".tar.gz"
            else:
                backup_filename += ".tar"
            
            backup_path = self.backup_root / job.destination / backup_filename
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # バックアップ実行
            files_backed_up, file_size = await self._create_backup_archive(
                job.source_paths, backup_path, job.compression
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = BackupResult(
                job_name=job_name,
                start_time=start_time,
                end_time=end_time,
                success=True,
                backup_path=str(backup_path),
                file_size=file_size,
                files_backed_up=files_backed_up
            )
            
            job.last_run = start_time
            self.backup_history.append(result)
            
            logger.info("backup_job_completed",
                       job=job_name,
                       duration=duration,
                       file_size=file_size,
                       files_count=files_backed_up,
                       backup_path=str(backup_path))
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = BackupResult(
                job_name=job_name,
                start_time=start_time,
                end_time=end_time,
                success=False,
                backup_path="",
                file_size=0,
                files_backed_up=0,
                error_message=str(e)
            )
            
            self.backup_history.append(result)
            
            logger.error("backup_job_failed",
                        job=job_name,
                        duration=duration,
                        error=str(e))
            
            return result
    
    async def _create_backup_archive(self, source_paths: List[str], 
                                   backup_path: Path, 
                                   compression: bool) -> tuple[int, int]:
        """バックアップアーカイブ作成"""
        files_count = 0
        
        mode = "w:gz" if compression else "w"
        
        with tarfile.open(backup_path, mode) as tar:
            for source_path in source_paths:
                source = Path(source_path)
                
                if source.exists():
                    if source.is_file():
                        tar.add(source, arcname=source.name)
                        files_count += 1
                    elif source.is_dir():
                        for file_path in source.rglob("*"):
                            if file_path.is_file():
                                # 相対パスを保持
                                arcname = file_path.relative_to(source.parent)
                                tar.add(file_path, arcname=arcname)
                                files_count += 1
                else:
                    logger.warning("backup_source_not_found", path=source_path)
        
        # ファイルサイズ取得
        file_size = backup_path.stat().st_size
        
        return files_count, file_size
    
    async def restore_from_backup(self, backup_path: str, 
                                destination: str = "/") -> bool:
        """バックアップから復元"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error("backup_file_not_found", path=backup_path)
            return False
        
        try:
            logger.info("restore_started", backup_path=backup_path, destination=destination)
            
            with tarfile.open(backup_file, "r:*") as tar:
                # 安全な復元のため、パスをチェック
                def is_safe_path(path: str) -> bool:
                    return not (path.startswith("/") or ".." in path)
                
                safe_members = [m for m in tar.getmembers() if is_safe_path(m.name)]
                
                tar.extractall(path=destination, members=safe_members)
            
            logger.info("restore_completed", 
                       backup_path=backup_path,
                       destination=destination,
                       files_restored=len(safe_members))
            
            return True
            
        except Exception as e:
            logger.error("restore_failed", 
                        backup_path=backup_path,
                        destination=destination,
                        error=str(e))
            return False
    
    async def _cleanup_old_backups(self):
        """古いバックアップファイルのクリーンアップ"""
        for job in self.jobs.values():
            if not job.enabled:
                continue
                
            backup_dir = self.backup_root / job.destination
            if not backup_dir.exists():
                continue
            
            cutoff_date = datetime.now() - timedelta(days=job.retention_days)
            deleted_files = []
            
            for backup_file in backup_dir.glob(f"{job.name}_*"):
                try:
                    file_stat = backup_file.stat()
                    file_date = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        deleted_files.append(str(backup_file))
                        
                except Exception as e:
                    logger.error("failed_to_delete_old_backup",
                               file=str(backup_file), error=str(e))
            
            if deleted_files:
                logger.info("old_backups_cleaned",
                           job=job.name,
                           deleted_count=len(deleted_files),
                           retention_days=job.retention_days)
    
    def add_backup_job(self, job: BackupJob) -> bool:
        """バックアップジョブ追加"""
        try:
            self.jobs[job.name] = job
            self._calculate_next_run(job)
            
            logger.info("backup_job_added",
                       job=job.name,
                       schedule=job.schedule,
                       next_run=job.next_run.isoformat() if job.next_run else None)
            return True
            
        except Exception as e:
            logger.error("failed_to_add_backup_job", 
                        job=job.name, error=str(e))
            return False
    
    def remove_backup_job(self, job_name: str) -> bool:
        """バックアップジョブ削除"""
        try:
            if job_name in self.jobs:
                del self.jobs[job_name]
                logger.info("backup_job_removed", job=job_name)
                return True
            return False
            
        except Exception as e:
            logger.error("failed_to_remove_backup_job",
                        job=job_name, error=str(e))
            return False
    
    def update_backup_job(self, job_name: str, updates: Dict[str, Any]) -> bool:
        """バックアップジョブ更新"""
        try:
            if job_name not in self.jobs:
                return False
            
            job = self.jobs[job_name]
            
            # 更新可能なフィールドのみ更新
            updatable_fields = [
                'source_paths', 'destination', 'schedule', 
                'retention_days', 'compression', 'enabled'
            ]
            
            for field, value in updates.items():
                if field in updatable_fields:
                    setattr(job, field, value)
            
            # スケジュールが変更された場合は次回実行時間を再計算
            if 'schedule' in updates:
                self._calculate_next_run(job)
            
            logger.info("backup_job_updated",
                       job=job_name,
                       updated_fields=list(updates.keys()))
            return True
            
        except Exception as e:
            logger.error("failed_to_update_backup_job",
                        job=job_name, error=str(e))
            return False
    
    def get_backup_status(self) -> Dict[str, Any]:
        """バックアップステータス取得"""
        status = {
            "scheduler_running": self.scheduler_running,
            "jobs": {},
            "recent_results": [],
            "storage_usage": {}
        }
        
        # ジョブ情報
        for job_name, job in self.jobs.items():
            status["jobs"][job_name] = {
                "enabled": job.enabled,
                "schedule": job.schedule,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "retention_days": job.retention_days
            }
        
        # 最近のバックアップ結果
        recent_results = sorted(
            self.backup_history, 
            key=lambda x: x.start_time, 
            reverse=True
        )[:10]
        
        status["recent_results"] = [
            {
                "job_name": result.job_name,
                "start_time": result.start_time.isoformat(),
                "success": result.success,
                "file_size": result.file_size,
                "files_backed_up": result.files_backed_up,
                "error_message": result.error_message
            }
            for result in recent_results
        ]
        
        # ストレージ使用量
        try:
            total_size = 0
            file_count = 0
            
            for backup_file in self.backup_root.rglob("*"):
                if backup_file.is_file():
                    total_size += backup_file.stat().st_size
                    file_count += 1
            
            status["storage_usage"] = {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "file_count": file_count,
                "backup_root": str(self.backup_root)
            }
            
        except Exception as e:
            logger.error("failed_to_calculate_storage_usage", error=str(e))
            status["storage_usage"] = {"error": str(e)}
        
        return status
    
    def list_backup_files(self, job_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """バックアップファイル一覧取得"""
        backup_files = []
        
        search_dirs = []
        if job_name and job_name in self.jobs:
            job_destination = self.jobs[job_name].destination
            search_dirs = [self.backup_root / job_destination]
        else:
            # 全ディレクトリを検索
            search_dirs = [d for d in self.backup_root.iterdir() if d.is_dir()]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            for backup_file in search_dir.glob("*"):
                if backup_file.is_file() and (
                    backup_file.suffix in ['.tar', '.gz'] or 
                    '.tar.gz' in backup_file.name
                ):
                    try:
                        stat = backup_file.stat()
                        backup_files.append({
                            "path": str(backup_file),
                            "name": backup_file.name,
                            "job_category": search_dir.name,
                            "size_bytes": stat.st_size,
                            "size_mb": round(stat.st_size / 1024 / 1024, 2),
                            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except Exception as e:
                        logger.error("failed_to_get_backup_file_info",
                                   file=str(backup_file), error=str(e))
        
        # 作成時間でソート（新しい順）
        backup_files.sort(key=lambda x: x["created_time"], reverse=True)
        
        return backup_files
    
    async def create_manual_backup(self, name: str, 
                                 source_paths: List[str],
                                 compression: bool = True) -> BackupResult:
        """手動バックアップ実行"""
        # 一時的なジョブを作成
        temp_job = BackupJob(
            name=f"manual_{name}",
            source_paths=source_paths,
            destination="manual",
            schedule="",  # 手動実行のためスケジュール無し
            compression=compression,
            enabled=False
        )
        
        return await self.run_backup_job(temp_job.name)

# グローバルインスタンス
_backup_service = None

def get_backup_service() -> BackupService:
    """バックアップサービスのシングルトンインスタンスを取得"""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service