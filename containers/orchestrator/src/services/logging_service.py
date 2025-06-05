"""
高度なログ管理・分析サービス
構造化ログ、ログローテーション、検索・分析機能を提供
"""
import os
import json
import gzip
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import structlog
import logging
import logging.handlers
from elasticsearch import AsyncElasticsearch
from enum import Enum

logger = structlog.get_logger()

class LogLevel(Enum):
    """ログレベル定義"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogEntry:
    """構造化ログエントリ"""
    timestamp: str
    level: str
    service: str
    message: str
    context: Dict[str, Any]
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class LogFilter:
    """ログフィルタ条件"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: Optional[str] = None
    service: Optional[str] = None
    message_contains: Optional[str] = None
    trace_id: Optional[str] = None
    limit: int = 100

class LoggingService:
    """高度なログ管理サービス"""
    
    def __init__(self, 
                 log_dir: str = "/var/log/aisemble",
                 elasticsearch_url: Optional[str] = None,
                 retention_days: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = retention_days
        self.elasticsearch_url = elasticsearch_url
        self.es_client: Optional[AsyncElasticsearch] = None
        
        # ログハンドラー設定
        self._setup_logging()
        
        # Elasticsearch接続（オプション）
        if elasticsearch_url:
            self._setup_elasticsearch()
        
        logger.info("logging_service_initialized",
                   log_dir=str(self.log_dir),
                   elasticsearch_enabled=bool(elasticsearch_url))
    
    def _setup_logging(self):
        """ロギング設定"""
        # ファイルハンドラー（JSON形式）
        json_formatter = logging.Formatter(
            '%(message)s'  # structlogで既にJSONフォーマット済み
        )
        
        # 日次ローテーションハンドラー
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "aisemble.log",
            when='midnight',
            interval=1,
            backupCount=self.retention_days,
            encoding='utf-8'
        )
        file_handler.setFormatter(json_formatter)
        
        # エラー専用ログファイル
        error_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "aisemble-error.log",
            when='midnight',
            interval=1,
            backupCount=self.retention_days,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        
        # 監査ログファイル
        audit_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "aisemble-audit.log",
            when='midnight',
            interval=1,
            backupCount=90,  # 監査ログは90日保持
            encoding='utf-8'
        )
        audit_handler.setFormatter(json_formatter)
        
        # ルートロガーに追加
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        
        # 監査ロガー
        audit_logger = logging.getLogger("audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
    
    def _setup_elasticsearch(self):
        """Elasticsearch設定"""
        try:
            self.es_client = AsyncElasticsearch([self.elasticsearch_url])
            logger.info("elasticsearch_client_initialized", url=self.elasticsearch_url)
        except Exception as e:
            logger.error("failed_to_initialize_elasticsearch", error=str(e))
            self.es_client = None
    
    async def log_structured(self, entry: LogEntry):
        """構造化ログ出力"""
        # ローカルファイルに出力
        log_data = asdict(entry)
        
        # 適切なロガーを選択
        if entry.level == "CRITICAL" or entry.level == "ERROR":
            logger.error(entry.message, **entry.context)
        elif entry.level == "WARNING":
            logger.warning(entry.message, **entry.context)
        elif entry.level == "INFO":
            logger.info(entry.message, **entry.context)
        else:
            logger.debug(entry.message, **entry.context)
        
        # Elasticsearchに送信（非同期）
        if self.es_client:
            await self._send_to_elasticsearch(log_data)
    
    async def _send_to_elasticsearch(self, log_data: Dict[str, Any]):
        """Elasticsearchにログデータを送信"""
        try:
            index_name = f"aisemble-logs-{datetime.now().strftime('%Y-%m')}"
            await self.es_client.index(
                index=index_name,
                body=log_data
            )
        except Exception as e:
            logger.error("failed_to_send_to_elasticsearch", error=str(e))
    
    async def search_logs(self, filter_conditions: LogFilter) -> List[Dict[str, Any]]:
        """ログ検索"""
        if self.es_client:
            return await self._search_elasticsearch(filter_conditions)
        else:
            return await self._search_local_files(filter_conditions)
    
    async def _search_elasticsearch(self, filter_conditions: LogFilter) -> List[Dict[str, Any]]:
        """Elasticsearchでログ検索"""
        try:
            query = {"bool": {"must": []}}
            
            # 時間範囲フィルタ
            if filter_conditions.start_time or filter_conditions.end_time:
                time_range = {}
                if filter_conditions.start_time:
                    time_range["gte"] = filter_conditions.start_time.isoformat()
                if filter_conditions.end_time:
                    time_range["lte"] = filter_conditions.end_time.isoformat()
                
                query["bool"]["must"].append({
                    "range": {"timestamp": time_range}
                })
            
            # レベルフィルタ
            if filter_conditions.level:
                query["bool"]["must"].append({
                    "term": {"level": filter_conditions.level}
                })
            
            # サービスフィルタ
            if filter_conditions.service:
                query["bool"]["must"].append({
                    "term": {"service": filter_conditions.service}
                })
            
            # メッセージ検索
            if filter_conditions.message_contains:
                query["bool"]["must"].append({
                    "match": {"message": filter_conditions.message_contains}
                })
            
            # トレースIDフィルタ
            if filter_conditions.trace_id:
                query["bool"]["must"].append({
                    "term": {"trace_id": filter_conditions.trace_id}
                })
            
            # 検索実行
            response = await self.es_client.search(
                index="aisemble-logs-*",
                body={
                    "query": query,
                    "size": filter_conditions.limit,
                    "sort": [{"timestamp": {"order": "desc"}}]
                }
            )
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
            
        except Exception as e:
            logger.error("elasticsearch_search_failed", error=str(e))
            return []
    
    async def _search_local_files(self, filter_conditions: LogFilter) -> List[Dict[str, Any]]:
        """ローカルファイルでログ検索"""
        results = []
        
        try:
            # 検索対象ファイルを決定
            log_files = self._get_log_files_in_range(
                filter_conditions.start_time,
                filter_conditions.end_time
            )
            
            for log_file in log_files:
                await self._search_single_file(log_file, filter_conditions, results)
                
                if len(results) >= filter_conditions.limit:
                    break
            
            # 時間順にソート
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return results[:filter_conditions.limit]
            
        except Exception as e:
            logger.error("local_log_search_failed", error=str(e))
            return []
    
    def _get_log_files_in_range(self, start_time: Optional[datetime], 
                               end_time: Optional[datetime]) -> List[Path]:
        """指定期間のログファイル一覧を取得"""
        log_files = []
        
        # メインログファイル
        main_log = self.log_dir / "aisemble.log"
        if main_log.exists():
            log_files.append(main_log)
        
        # ローテーションされたファイル
        for file_path in self.log_dir.glob("aisemble.log.*"):
            if file_path.suffix in ['.gz', '.1', '.2', '.3', '.4', '.5']:
                log_files.append(file_path)
        
        return sorted(log_files, reverse=True)  # 新しいファイルから
    
    async def _search_single_file(self, file_path: Path, 
                                 filter_conditions: LogFilter,
                                 results: List[Dict[str, Any]]):
        """単一ログファイルを検索"""
        try:
            if file_path.suffix == '.gz':
                # 圧縮ファイル
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    await self._process_log_lines(f, filter_conditions, results)
            else:
                # 通常ファイル
                with open(file_path, 'r', encoding='utf-8') as f:
                    await self._process_log_lines(f, filter_conditions, results)
                    
        except Exception as e:
            logger.error("failed_to_search_log_file", 
                        file=str(file_path), error=str(e))
    
    async def _process_log_lines(self, file_handle, 
                               filter_conditions: LogFilter,
                               results: List[Dict[str, Any]]):
        """ログ行を処理してフィルタリング"""
        line_count = 0
        
        for line in file_handle:
            line_count += 1
            
            # 大量ファイル処理時の非同期制御
            if line_count % 1000 == 0:
                await asyncio.sleep(0.001)
            
            try:
                log_entry = json.loads(line.strip())
                
                # フィルタ条件チェック
                if self._matches_filter(log_entry, filter_conditions):
                    results.append(log_entry)
                    
                    if len(results) >= filter_conditions.limit:
                        break
                        
            except json.JSONDecodeError:
                continue  # 不正なJSON行はスキップ
    
    def _matches_filter(self, log_entry: Dict[str, Any], 
                       filter_conditions: LogFilter) -> bool:
        """ログエントリがフィルタ条件にマッチするかチェック"""
        # 時間範囲チェック
        if filter_conditions.start_time or filter_conditions.end_time:
            try:
                entry_time = datetime.fromisoformat(log_entry.get("timestamp", ""))
                
                if filter_conditions.start_time and entry_time < filter_conditions.start_time:
                    return False
                if filter_conditions.end_time and entry_time > filter_conditions.end_time:
                    return False
            except ValueError:
                return False
        
        # レベルチェック
        if filter_conditions.level:
            if log_entry.get("level") != filter_conditions.level:
                return False
        
        # サービスチェック
        if filter_conditions.service:
            if log_entry.get("service") != filter_conditions.service:
                return False
        
        # メッセージ検索
        if filter_conditions.message_contains:
            message = log_entry.get("message", "").lower()
            if filter_conditions.message_contains.lower() not in message:
                return False
        
        # トレースIDチェック
        if filter_conditions.trace_id:
            if log_entry.get("trace_id") != filter_conditions.trace_id:
                return False
        
        return True
    
    async def get_log_stats(self, hours: int = 24) -> Dict[str, Any]:
        """ログ統計情報を取得"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        filter_conditions = LogFilter(
            start_time=start_time,
            end_time=end_time,
            limit=10000  # 統計用に多めに取得
        )
        
        logs = await self.search_logs(filter_conditions)
        
        # 統計計算
        stats = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "total_entries": len(logs),
            "level_distribution": {},
            "service_distribution": {},
            "hourly_distribution": {},
            "error_rate": 0.0,
            "top_errors": []
        }
        
        # レベル別分布
        for log_entry in logs:
            level = log_entry.get("level", "UNKNOWN")
            stats["level_distribution"][level] = stats["level_distribution"].get(level, 0) + 1
        
        # サービス別分布
        for log_entry in logs:
            service = log_entry.get("service", "unknown")
            stats["service_distribution"][service] = stats["service_distribution"].get(service, 0) + 1
        
        # エラー率計算
        error_count = stats["level_distribution"].get("ERROR", 0) + stats["level_distribution"].get("CRITICAL", 0)
        if len(logs) > 0:
            stats["error_rate"] = (error_count / len(logs)) * 100
        
        return stats
    
    async def audit_log(self, action: str, user_id: str, resource: str, 
                       details: Dict[str, Any], success: bool = True):
        """監査ログ記録"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "success": success,
            "details": details,
            "service": "audit"
        }
        
        # 監査専用ロガーに出力
        audit_logger = logging.getLogger("audit")
        audit_logger.info(json.dumps(audit_entry, ensure_ascii=False))
        
        # Elasticsearchにも送信
        if self.es_client:
            try:
                index_name = f"aisemble-audit-{datetime.now().strftime('%Y-%m')}"
                await self.es_client.index(
                    index=index_name,
                    body=audit_entry
                )
            except Exception as e:
                logger.error("failed_to_send_audit_to_elasticsearch", error=str(e))
    
    async def cleanup_old_logs(self):
        """古いログファイルのクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        deleted_files = []
        for log_file in self.log_dir.glob("*.log.*"):
            try:
                file_stat = log_file.stat()
                file_date = datetime.fromtimestamp(file_stat.st_mtime)
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_files.append(str(log_file))
            except Exception as e:
                logger.error("failed_to_delete_old_log", 
                           file=str(log_file), error=str(e))
        
        if deleted_files:
            logger.info("old_logs_cleaned_up", 
                       deleted_count=len(deleted_files),
                       retention_days=self.retention_days)
        
        return deleted_files
    
    async def export_logs(self, filter_conditions: LogFilter, 
                         export_format: str = "json") -> str:
        """ログのエクスポート"""
        logs = await self.search_logs(filter_conditions)
        
        if export_format == "json":
            return json.dumps(logs, indent=2, ensure_ascii=False)
        elif export_format == "csv":
            return self._logs_to_csv(logs)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def _logs_to_csv(self, logs: List[Dict[str, Any]]) -> str:
        """ログをCSV形式に変換"""
        if not logs:
            return ""
        
        import csv
        import io
        
        output = io.StringIO()
        
        # ヘッダー抽出
        headers = set()
        for log_entry in logs:
            headers.update(log_entry.keys())
        
        headers = sorted(headers)
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for log_entry in logs:
            # 複雑なオブジェクトはJSON文字列に変換
            row = {}
            for key, value in log_entry.items():
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = str(value) if value is not None else ""
            writer.writerow(row)
        
        return output.getvalue()

# グローバルインスタンス
_logging_service = None

def get_logging_service() -> LoggingService:
    """ログサービスのシングルトンインスタンスを取得"""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service