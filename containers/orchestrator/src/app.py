"""
Ai-semble v2 Orchestrator Service
メインのオーケストレーションサービス
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse

from api import health, ai, jobs, models, operations
from config.settings import get_settings

# 構造化ロギング設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheusメトリクス
REQUEST_COUNT = Counter('requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'HTTP request duration')

app = FastAPI(
    title="Ai-semble v2 Orchestrator",
    description="AI オーケストレーションプラットフォーム",
    version="2.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(operations.router, prefix="/ops", tags=["operations"])

@app.get("/metrics")
async def metrics():
    """Prometheusメトリクス公開"""
    return PlainTextResponse(generate_latest())

@app.on_event("startup")
async def startup_event():
    logger.info("orchestrator_startup", service="orchestrator", version="2.0.0")
    
    # 運用サービス初期化
    from services.monitoring import get_monitoring_service
    from services.backup_service import get_backup_service
    
    # 監視サービス開始
    monitoring = get_monitoring_service()
    await monitoring.start_monitoring()
    
    # バックアップスケジューラー開始
    backup_service = get_backup_service()
    await backup_service.start_scheduler()
    
    logger.info("operations_services_started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("orchestrator_shutdown", service="orchestrator")
    
    # 運用サービス停止
    from services.monitoring import get_monitoring_service
    from services.backup_service import get_backup_service
    
    monitoring = get_monitoring_service()
    await monitoring.stop_monitoring()
    
    backup_service = get_backup_service()
    await backup_service.stop_scheduler()
    
    logger.info("operations_services_stopped")

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )