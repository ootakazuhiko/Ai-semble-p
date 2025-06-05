"""
Orchestrator Health API テスト
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../containers/orchestrator/src'))

from app import app

client = TestClient(app)

def test_health_endpoint():
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "orchestrator"
    assert data["version"] == "2.0.0"

def test_readiness_endpoint():
    """レディネスチェックエンドポイントのテスト"""
    response = client.get("/health/ready")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ready"
    assert "timestamp" in data

def test_liveness_endpoint():
    """ライブネスチェックエンドポイントのテスト"""
    response = client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "alive"
    assert "timestamp" in data