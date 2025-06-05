"""
設定管理
"""
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # サービス設定
    service_name: str = "orchestrator"
    service_version: str = "2.0.0"
    
    # AI Services接続設定
    llm_service_url: str = "http://localhost:8081"
    vision_service_url: str = "http://localhost:8082"
    nlp_service_url: str = "http://localhost:8083"
    
    # Data Processor接続設定
    data_processor_url: str = "http://localhost:8084"
    
    # ログレベル
    log_level: str = "INFO"
    
    # 認証設定
    enable_auth: bool = False
    secret_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    """設定インスタンスを取得"""
    return Settings()