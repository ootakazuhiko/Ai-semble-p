"""
包括的監視・メトリクス収集サービス
Prometheus、ヘルスチェック、アラート機能を統合
"""
import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import structlog
from prometheus_client import Counter, Histogram, Gauge, Info
import aiohttp
import json

logger = structlog.get_logger()

# Prometheusメトリクス定義
REQUEST_COUNT = Counter(
    'aisemble_requests_total', 
    'Total number of requests', 
    ['service', 'endpoint', 'method', 'status_code']
)

REQUEST_DURATION = Histogram(
    'aisemble_request_duration_seconds',
    'Request duration in seconds',
    ['service', 'endpoint', 'method']
)

ACTIVE_CONNECTIONS = Gauge(
    'aisemble_active_connections',
    'Number of active connections',
    ['service']
)

SYSTEM_CPU_USAGE = Gauge(
    'aisemble_system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'aisemble_system_memory_usage_percent', 
    'System memory usage percentage'
)

SYSTEM_DISK_USAGE = Gauge(
    'aisemble_system_disk_usage_percent',
    'System disk usage percentage'
)

MODEL_INFERENCE_COUNT = Counter(
    'aisemble_model_inference_total',
    'Total number of model inferences',
    ['model_name', 'task_type', 'status']
)

MODEL_INFERENCE_DURATION = Histogram(
    'aisemble_model_inference_duration_seconds',
    'Model inference duration in seconds',
    ['model_name', 'task_type']
)

ERROR_COUNT = Counter(
    'aisemble_errors_total',
    'Total number of errors',
    ['service', 'error_type', 'severity']
)

@dataclass
class ServiceHealth:
    """サービスヘルス状態"""
    name: str
    url: str
    status: str = "unknown"  # healthy, unhealthy, unknown
    response_time: float = 0.0
    last_check: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    uptime_percent: float = 100.0
    consecutive_failures: int = 0

@dataclass
class AlertRule:
    """アラートルール定義"""
    name: str
    condition: str  # cpu_usage > 80, memory_usage > 90, etc.
    threshold: float
    duration: int  # seconds
    severity: str = "warning"  # info, warning, critical
    enabled: bool = True
    last_triggered: Optional[datetime] = None

class MonitoringService:
    """包括的監視サービス"""
    
    def __init__(self):
        self.services: Dict[str, ServiceHealth] = {}
        self.alert_rules: List[AlertRule] = []
        self.system_metrics: Dict[str, Any] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # デフォルトサービス設定
        self._setup_default_services()
        self._setup_default_alert_rules()
        
        logger.info("monitoring_service_initialized")
    
    def _setup_default_services(self):
        """デフォルトサービス監視設定"""
        default_services = [
            {"name": "orchestrator", "url": "http://localhost:8080/health"},
            {"name": "llm-service", "url": "http://localhost:8081/health"},
            {"name": "vision-service", "url": "http://localhost:8082/health"},
            {"name": "nlp-service", "url": "http://localhost:8083/health"},
            {"name": "data-processor", "url": "http://localhost:8084/health"}
        ]
        
        for service in default_services:
            self.services[service["name"]] = ServiceHealth(
                name=service["name"],
                url=service["url"]
            )
    
    def _setup_default_alert_rules(self):
        """デフォルトアラートルール設定"""
        self.alert_rules = [
            AlertRule("high_cpu_usage", "cpu_usage", 80.0, 300, "warning"),
            AlertRule("critical_cpu_usage", "cpu_usage", 95.0, 60, "critical"),
            AlertRule("high_memory_usage", "memory_usage", 85.0, 300, "warning"),
            AlertRule("critical_memory_usage", "memory_usage", 95.0, 60, "critical"),
            AlertRule("high_disk_usage", "disk_usage", 80.0, 600, "warning"),
            AlertRule("critical_disk_usage", "disk_usage", 90.0, 300, "critical"),
            AlertRule("service_down", "service_health", 0.0, 60, "critical"),
            AlertRule("high_error_rate", "error_rate", 5.0, 300, "warning")
        ]
    
    async def start_monitoring(self):
        """監視開始"""
        if self.monitoring_active:
            logger.warning("monitoring_already_active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("monitoring_started")
    
    async def stop_monitoring(self):
        """監視停止"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("monitoring_stopped")
    
    async def _monitoring_loop(self):
        """メイン監視ループ"""
        while self.monitoring_active:
            try:
                # システムメトリクス収集
                await self._collect_system_metrics()
                
                # サービスヘルスチェック
                await self._check_services_health()
                
                # アラート評価
                await self._evaluate_alerts()
                
                # Prometheusメトリクス更新
                self._update_prometheus_metrics()
                
                await asyncio.sleep(30)  # 30秒間隔
                
            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def _collect_system_metrics(self):
        """システムメトリクス収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # ネットワーク統計
            network = psutil.net_io_counters()
            
            # プロセス数
            process_count = len(psutil.pids())
            
            self.system_metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_usage": disk_percent,
                "disk_total": disk.total,
                "disk_free": disk.free,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "process_count": process_count
            }
            
            logger.debug("system_metrics_collected", 
                        cpu=cpu_percent,
                        memory=memory_percent,
                        disk=disk_percent)
                        
        except Exception as e:
            logger.error("failed_to_collect_system_metrics", error=str(e))
    
    async def _check_services_health(self):
        """サービスヘルスチェック"""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for service_name, service in self.services.items():
                await self._check_single_service_health(session, service)
    
    async def _check_single_service_health(self, session: aiohttp.ClientSession, service: ServiceHealth):
        """単一サービスのヘルスチェック"""
        start_time = time.time()
        
        try:
            async with session.get(service.url) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    service.status = "healthy"
                    service.consecutive_failures = 0
                    service.error_message = None
                else:
                    service.status = "unhealthy"
                    service.consecutive_failures += 1
                    service.error_message = f"HTTP {response.status}"
                
                service.response_time = response_time
                service.last_check = datetime.now()
                
                logger.debug("service_health_checked",
                           service=service.name,
                           status=service.status,
                           response_time=response_time)
                
        except Exception as e:
            response_time = time.time() - start_time
            service.status = "unhealthy"
            service.consecutive_failures += 1
            service.error_message = str(e)
            service.response_time = response_time
            service.last_check = datetime.now()
            
            logger.warning("service_health_check_failed",
                          service=service.name,
                          error=str(e))
    
    async def _evaluate_alerts(self):
        """アラート評価・発火"""
        current_time = datetime.now()
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            should_trigger = False
            
            # 条件評価
            if rule.condition == "cpu_usage":
                current_value = self.system_metrics.get("cpu_usage", 0)
                should_trigger = current_value > rule.threshold
            elif rule.condition == "memory_usage":
                current_value = self.system_metrics.get("memory_usage", 0)
                should_trigger = current_value > rule.threshold
            elif rule.condition == "disk_usage":
                current_value = self.system_metrics.get("disk_usage", 0)
                should_trigger = current_value > rule.threshold
            elif rule.condition == "service_health":
                unhealthy_services = [s for s in self.services.values() if s.status == "unhealthy"]
                should_trigger = len(unhealthy_services) > rule.threshold
            
            # アラート発火判定
            if should_trigger:
                time_since_last_trigger = timedelta(seconds=rule.duration)
                if (rule.last_triggered is None or 
                    current_time - rule.last_triggered > time_since_last_trigger):
                    
                    await self._trigger_alert(rule, current_time)
    
    async def _trigger_alert(self, rule: AlertRule, timestamp: datetime):
        """アラート発火"""
        alert_data = {
            "rule_name": rule.name,
            "severity": rule.severity,
            "condition": rule.condition,
            "threshold": rule.threshold,
            "timestamp": timestamp.isoformat(),
            "system_metrics": self.system_metrics.copy(),
            "services_status": {name: service.status for name, service in self.services.items()}
        }
        
        self.alert_history.append(alert_data)
        rule.last_triggered = timestamp
        
        logger.warning("alert_triggered",
                      rule=rule.name,
                      severity=rule.severity,
                      condition=rule.condition,
                      threshold=rule.threshold)
        
        # アラート通知処理（将来の拡張ポイント）
        await self._send_alert_notification(alert_data)
    
    async def _send_alert_notification(self, alert_data: Dict[str, Any]):
        """アラート通知送信（拡張可能）"""
        # 将来的にSlack、Email、PagerDuty等との統合
        logger.info("alert_notification_placeholder", alert=alert_data)
    
    def _update_prometheus_metrics(self):
        """Prometheusメトリクス更新"""
        try:
            # システムメトリクス
            if self.system_metrics:
                SYSTEM_CPU_USAGE.set(self.system_metrics.get("cpu_usage", 0))
                SYSTEM_MEMORY_USAGE.set(self.system_metrics.get("memory_usage", 0))
                SYSTEM_DISK_USAGE.set(self.system_metrics.get("disk_usage", 0))
            
            # サービスヘルス
            for service_name, service in self.services.items():
                # アクティブ接続数（簡易実装）
                if service.status == "healthy":
                    ACTIVE_CONNECTIONS.labels(service=service_name).set(1)
                else:
                    ACTIVE_CONNECTIONS.labels(service=service_name).set(0)
                
        except Exception as e:
            logger.error("failed_to_update_prometheus_metrics", error=str(e))
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム全体の状況取得"""
        healthy_services = [s for s in self.services.values() if s.status == "healthy"]
        unhealthy_services = [s for s in self.services.values() if s.status == "unhealthy"]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy" if len(unhealthy_services) == 0 else "degraded",
            "services": {
                "total": len(self.services),
                "healthy": len(healthy_services),
                "unhealthy": len(unhealthy_services)
            },
            "system_metrics": self.system_metrics,
            "recent_alerts": self.alert_history[-10:],  # 最新10件
            "services_detail": {
                name: {
                    "status": service.status,
                    "response_time": service.response_time,
                    "last_check": service.last_check.isoformat(),
                    "consecutive_failures": service.consecutive_failures,
                    "error_message": service.error_message
                }
                for name, service in self.services.items()
            }
        }
    
    def add_service(self, name: str, url: str) -> bool:
        """監視対象サービス追加"""
        try:
            self.services[name] = ServiceHealth(name=name, url=url)
            logger.info("monitoring_service_added", name=name, url=url)
            return True
        except Exception as e:
            logger.error("failed_to_add_monitoring_service", name=name, error=str(e))
            return False
    
    def remove_service(self, name: str) -> bool:
        """監視対象サービス削除"""
        try:
            if name in self.services:
                del self.services[name]
                logger.info("monitoring_service_removed", name=name)
                return True
            return False
        except Exception as e:
            logger.error("failed_to_remove_monitoring_service", name=name, error=str(e))
            return False
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """アラートルール追加"""
        try:
            self.alert_rules.append(rule)
            logger.info("alert_rule_added", rule_name=rule.name)
            return True
        except Exception as e:
            logger.error("failed_to_add_alert_rule", rule_name=rule.name, error=str(e))
            return False
    
    def record_model_inference(self, model_name: str, task_type: str, 
                             duration: float, status: str = "success"):
        """モデル推論メトリクス記録"""
        MODEL_INFERENCE_COUNT.labels(
            model_name=model_name,
            task_type=task_type,
            status=status
        ).inc()
        
        if status == "success":
            MODEL_INFERENCE_DURATION.labels(
                model_name=model_name,
                task_type=task_type
            ).observe(duration)
    
    def record_request(self, service: str, endpoint: str, method: str, 
                      status_code: int, duration: float):
        """リクエストメトリクス記録"""
        REQUEST_COUNT.labels(
            service=service,
            endpoint=endpoint,
            method=method,
            status_code=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            service=service,
            endpoint=endpoint,
            method=method
        ).observe(duration)
    
    def record_error(self, service: str, error_type: str, severity: str = "error"):
        """エラーメトリクス記録"""
        ERROR_COUNT.labels(
            service=service,
            error_type=error_type,
            severity=severity
        ).inc()

# グローバルインスタンス
_monitoring_service = None

def get_monitoring_service() -> MonitoringService:
    """監視サービスのシングルトンインスタンスを取得"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service