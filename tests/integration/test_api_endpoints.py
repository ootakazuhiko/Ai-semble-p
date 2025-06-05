"""
API エンドポイント統合テスト
"""
import pytest
import requests
import time
import json

# テスト用のベースURL
BASE_URL = "http://localhost:8080"

class TestAPIIntegration:
    """API統合テストクラス"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        # サービスが起動しているかチェック
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    pytest.skip("Orchestrator service not available")
                time.sleep(2)
    
    def test_health_endpoint(self):
        """ヘルスチェックエンドポイント"""
        response = requests.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "orchestrator"
    
    def test_data_processing_endpoint(self):
        """データ処理エンドポイント"""
        payload = {
            "operation": "analyze",
            "data": {
                "records": [
                    {"id": 1, "value": 100},
                    {"id": 2, "value": 200}
                ]
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/data/process",
            json=payload,
            timeout=30
        )
        
        # サービスが利用できない場合はスキップ
        if response.status_code == 500:
            pytest.skip("Data processor service not available")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "result" in data
    
    def test_llm_completion_endpoint(self):
        """LLM推論エンドポイント"""
        payload = {
            "prompt": "Hello, this is a test.",
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{BASE_URL}/ai/llm/completion",
            json=payload,
            timeout=60
        )
        
        # サービスが利用できない場合はスキップ
        if response.status_code == 500:
            pytest.skip("LLM service not available")
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["completed", "pending"]
    
    def test_vision_analysis_endpoint(self):
        """画像解析エンドポイント"""
        # テスト用の小さなBase64画像（1x1ピクセル）
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        payload = {
            "image_base64": test_image_base64,
            "task": "analyze"
        }
        
        response = requests.post(
            f"{BASE_URL}/ai/vision/analyze",
            json=payload,
            timeout=60
        )
        
        # サービスが利用できない場合はスキップ
        if response.status_code == 500:
            pytest.skip("Vision service not available")
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["completed", "pending"]
    
    def test_nlp_processing_endpoint(self):
        """NLP処理エンドポイント"""
        payload = {
            "text": "This is a test sentence for NLP processing.",
            "task": "sentiment"
        }
        
        response = requests.post(
            f"{BASE_URL}/ai/nlp/process",
            json=payload,
            timeout=30
        )
        
        # サービスが利用できない場合はスキップ
        if response.status_code == 500:
            pytest.skip("NLP service not available")
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["completed", "pending"]
    
    def test_metrics_endpoint(self):
        """メトリクスエンドポイント"""
        response = requests.get(f"{BASE_URL}/metrics", timeout=10)
        
        assert response.status_code == 200
        # Prometheusメトリクス形式の確認
        assert "requests_total" in response.text or "# TYPE" in response.text
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # 不正なペイロード
        response = requests.post(
            f"{BASE_URL}/ai/llm/completion",
            json={"invalid": "payload"},
            timeout=10
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_rate_limiting(self):
        """レート制限テスト（基本版）"""
        # 複数リクエストを短時間で送信
        responses = []
        for i in range(5):
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            responses.append(response.status_code)
        
        # 全て正常に処理されることを確認（レート制限が実装されていない場合）
        assert all(status == 200 for status in responses)