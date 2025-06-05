# Ai-semble v2 API使用例集

## 📋 目次

1. [基本的なAPI呼び出し](#基本的なapi呼び出し)
2. [実用的なワークフロー例](#実用的なワークフロー例)
3. [エラーハンドリング](#エラーハンドリング)
4. [パフォーマンス最適化](#パフォーマンス最適化)
5. [SDK・ライブラリ使用例](#sdkライブラリ使用例)

## 🚀 基本的なAPI呼び出し

### ヘルスチェック

```bash
# 基本的なヘルスチェック
curl -X GET http://localhost:8080/health

# レスポンス例
{
  "status": "healthy",
  "timestamp": 1701234567.89,
  "service": "orchestrator", 
  "version": "2.0.0"
}
```

### LLM推論

```bash
# シンプルなテキスト生成
curl -X POST http://localhost:8080/ai/llm/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "AIとは何かを100文字以内で説明してください",
    "max_tokens": 150,
    "temperature": 0.7
  }'

# レスポンス例
{
  "job_id": "llm-20241205-001",
  "status": "completed",
  "result": "AIは人工知能のことで、人間の知的な活動をコンピューターで模倣する技術です。機械学習やディープラーニングを活用して、データから学習し問題解決や予測を行います。",
  "tokens_used": 87
}
```

### データ処理

```bash
# データ分析
curl -X POST http://localhost:8080/data/process \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "analyze",
    "data": {
      "records": [
        {"name": "Alice", "age": 25, "score": 85},
        {"name": "Bob", "age": 30, "score": 92},
        {"name": "Carol", "age": 28, "score": 78}
      ]
    }
  }'

# レスポンス例
{
  "status": "completed",
  "result": {
    "shape": [3, 3],
    "numeric_summary": {
      "age": {"mean": 27.67, "std": 2.52},
      "score": {"mean": 85.0, "std": 7.0}
    },
    "missing_values": {"age": 0, "score": 0}
  },
  "rows_processed": 3,
  "processing_time": 0.15
}
```

## 💼 実用的なワークフロー例

### 1. 顧客フィードバック分析パイプライン

```bash
#!/bin/bash
# feedback_analysis.sh

BASE_URL="http://localhost:8080"

# Step 1: データアップロード
echo "1. データをアップロード中..."
UPLOAD_RESPONSE=$(curl -s -X POST $BASE_URL/data/upload \
  -F "file=@customer_feedback.csv")
echo $UPLOAD_RESPONSE

# Step 2: 基本統計分析
echo "2. 基本統計分析実行中..."
ANALYSIS_RESPONSE=$(curl -s -X POST $BASE_URL/data/process \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "analyze",
    "data": {"file_path": "/data/customer_feedback.csv"}
  }')
echo $ANALYSIS_RESPONSE

# Step 3: 感情分析（LLM使用）
echo "3. 感情分析実行中..."
SENTIMENT_RESPONSE=$(curl -s -X POST $BASE_URL/ai/llm/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "以下の顧客フィードバックデータの感情傾向を分析し、主要な不満点を3つ挙げてください:\n[データサマリーをここに挿入]",
    "max_tokens": 300,
    "temperature": 0.3
  }')
echo $SENTIMENT_RESPONSE

# Step 4: 改善提案生成
echo "4. 改善提案生成中..."
SUGGESTION_RESPONSE=$(curl -s -X POST $BASE_URL/ai/llm/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "顧客の主要不満点に基づいて、具体的な改善策を優先度順に5つ提案してください",
    "max_tokens": 400,
    "temperature": 0.5
  }')
echo $SUGGESTION_RESPONSE
```

### 2. 画像解析＋レポート生成

```python
import requests
import json
import time

class ImageAnalysisWorkflow:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def analyze_image_batch(self, image_urls, analysis_type="general"):
        """複数画像の一括解析"""
        results = []
        
        for i, url in enumerate(image_urls):
            print(f"画像 {i+1}/{len(image_urls)} を解析中...")
            
            response = requests.post(
                f"{self.base_url}/ai/vision/analyze",
                json={
                    "image_url": url,
                    "task": analysis_type,
                    "options": {"confidence_threshold": 0.8}
                }
            )
            
            if response.status_code == 200:
                results.append(response.json())
            else:
                print(f"Error analyzing image {url}: {response.text}")
            
            time.sleep(1)  # APIレート制限対応
            
        return results
    
    def generate_report(self, analysis_results):
        """解析結果からレポート生成"""
        summary_prompt = f"""
        以下の画像解析結果をもとに、包括的なレポートを作成してください:
        
        解析結果: {json.dumps(analysis_results, indent=2)}
        
        レポートには以下を含めてください:
        1. 全体的な傾向
        2. 注目すべき発見
        3. 推奨アクション
        """
        
        response = requests.post(
            f"{self.base_url}/ai/llm/completion",
            json={
                "prompt": summary_prompt,
                "max_tokens": 800,
                "temperature": 0.4
            }
        )
        
        return response.json()

# 使用例
workflow = ImageAnalysisWorkflow()

image_urls = [
    "https://example.com/product1.jpg",
    "https://example.com/product2.jpg", 
    "https://example.com/product3.jpg"
]

# 画像解析実行
analysis_results = workflow.analyze_image_batch(image_urls, "product_quality")

# レポート生成
report = workflow.generate_report(analysis_results)
print("=== 解析レポート ===")
print(report["result"])
```

### 3. リアルタイム監視・アラート

```python
import requests
import time
import json
from datetime import datetime

class AiSembleMonitor:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.alert_conditions = {
            "response_time_threshold": 5.0,
            "error_rate_threshold": 0.1
        }
    
    def check_health(self):
        """ヘルスチェック実行"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response_time,
                "timestamp": datetime.now().isoformat(),
                "details": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "status": "error",
                "response_time": None,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def check_ai_services(self):
        """AI各サービスの動作確認"""
        services = {
            "llm": {
                "endpoint": "/ai/llm/completion",
                "test_payload": {
                    "prompt": "Health check test",
                    "max_tokens": 10,
                    "temperature": 0.1
                }
            },
            "data_processor": {
                "endpoint": "/data/process",
                "test_payload": {
                    "operation": "analyze",
                    "data": {"records": [{"test": 1}]}
                }
            }
        }
        
        results = {}
        for service_name, config in services.items():
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}{config['endpoint']}",
                    json=config["test_payload"],
                    timeout=30
                )
                response_time = time.time() - start_time
                
                results[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response_time,
                    "error": None if response.status_code == 200 else response.text
                }
            except Exception as e:
                results[service_name] = {
                    "status": "error",
                    "response_time": None,
                    "error": str(e)
                }
        
        return results
    
    def run_monitoring_loop(self, interval=60):
        """継続的監視ループ"""
        print("Ai-semble v2 監視開始...")
        
        while True:
            try:
                # ヘルスチェック
                health = self.check_health()
                print(f"[{health['timestamp']}] Health: {health['status']} ({health.get('response_time', 'N/A')}s)")
                
                # サービスチェック
                services = self.check_ai_services()
                for service, status in services.items():
                    print(f"  {service}: {status['status']} ({status.get('response_time', 'N/A')}s)")
                
                # アラート判定
                if health['status'] != 'healthy':
                    self.send_alert(f"Platform health check failed: {health}")
                
                for service, status in services.items():
                    if status['status'] != 'healthy':
                        self.send_alert(f"Service {service} is unhealthy: {status}")
                    elif status['response_time'] and status['response_time'] > self.alert_conditions['response_time_threshold']:
                        self.send_alert(f"Service {service} response time high: {status['response_time']}s")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("監視を停止します...")
                break
            except Exception as e:
                print(f"監視エラー: {e}")
                time.sleep(interval)
    
    def send_alert(self, message):
        """アラート送信（ログ出力・外部通知）"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": "WARNING",
            "message": message
        }
        print(f"🚨 ALERT: {json.dumps(alert)}")
        # ここで実際の通知（Slack、メール等）を実装

# 使用例
if __name__ == "__main__":
    monitor = AiSembleMonitor()
    monitor.run_monitoring_loop(interval=30)  # 30秒間隔で監視
```

## 🚨 エラーハンドリング

### Pythonでの堅牢なエラーハンドリング

```python
import requests
import time
from typing import Dict, Any, Optional

class AiSembleClient:
    def __init__(self, base_url: str = "http://localhost:8080", max_retries: int = 3):
        self.base_url = base_url
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """リトライ機能付きリクエスト実行"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code >= 500:  # Server error
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Server error. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"Server error: {response.status_code}",
                            "details": response.text
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Client error: {response.status_code}",
                        "details": response.text
                    }
                    
            except requests.exceptions.ConnectionError:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Connection error. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "success": False,
                        "error": "Connection failed after retries"
                    }
            except requests.exceptions.Timeout:
                return {
                    "success": False,
                    "error": "Request timeout"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}"
                }
        
        return {"success": False, "error": "Max retries exceeded"}
    
    def llm_completion(self, prompt: str, **options) -> Dict[str, Any]:
        """エラーハンドリング付きLLM推論"""
        payload = {"prompt": prompt, **options}
        result = self.make_request("POST", "/ai/llm/completion", json=payload)
        
        if not result["success"]:
            print(f"LLM completion failed: {result['error']}")
            return result
        
        # ジョブIDがある場合は結果を待機
        job_id = result["data"].get("job_id")
        if job_id and result["data"].get("status") == "pending":
            return self.wait_for_job_completion(job_id)
        
        return result
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """ジョブ完了を待機"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.make_request("GET", f"/jobs/{job_id}")
            
            if not result["success"]:
                return result
            
            status = result["data"]["status"]
            if status == "completed":
                return {"success": True, "data": result["data"]}
            elif status == "failed":
                return {
                    "success": False,
                    "error": "Job failed",
                    "details": result["data"].get("error")
                }
            
            time.sleep(2)  # 2秒間隔でポーリング
        
        return {"success": False, "error": "Job timeout"}

# 使用例
client = AiSembleClient()

# エラーハンドリング付きでLLM実行
result = client.llm_completion(
    "Pythonの特徴を説明してください",
    max_tokens=200,
    temperature=0.7
)

if result["success"]:
    print("成功:", result["data"]["result"])
else:
    print("エラー:", result["error"])
```

## ⚡ パフォーマンス最適化

### バッチ処理の最適化

```python
import asyncio
import aiohttp
from typing import List, Dict, Any

class AsyncAiSembleClient:
    def __init__(self, base_url: str = "http://localhost:8080", max_concurrent: int = 5):
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def make_async_request(self, session: aiohttp.ClientSession, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """非同期リクエスト実行"""
        async with self.semaphore:
            try:
                url = f"{self.base_url}{endpoint}"
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"success": True, "data": data}
                    else:
                        text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "details": text
                        }
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def batch_llm_completion(self, prompts: List[str], **options) -> List[Dict[str, Any]]:
        """複数プロンプトの並列処理"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for prompt in prompts:
                payload = {"prompt": prompt, **options}
                task = self.make_async_request(
                    session, "POST", "/ai/llm/completion", json=payload
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
    
    async def batch_data_processing(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """複数データ処理の並列実行"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for operation in operations:
                task = self.make_async_request(
                    session, "POST", "/data/process", json=operation
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results

# 使用例
async def main():
    client = AsyncAiSembleClient(max_concurrent=3)
    
    # 複数のLLM推論を並列実行
    prompts = [
        "AIの歴史について教えてください",
        "機械学習とディープラーニングの違いは？",
        "自然言語処理の応用例を挙げてください"
    ]
    
    results = await client.batch_llm_completion(
        prompts,
        max_tokens=150,
        temperature=0.7
    )
    
    for i, result in enumerate(results):
        if result["success"]:
            print(f"プロンプト {i+1}: {result['data']['result'][:100]}...")
        else:
            print(f"プロンプト {i+1} エラー: {result['error']}")

# 実行
asyncio.run(main())
```

## 📚 SDK・ライブラリ使用例

### カスタムSDKクラス

```python
# ai_semble_sdk.py
import requests
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class JobResult:
    job_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AiSembleSDK:
    """Ai-semble v2 公式SDK"""
    
    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def health(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def llm_completion(self, prompt: str, model: str = "default", 
                      max_tokens: int = 1000, temperature: float = 0.7) -> JobResult:
        """LLM推論実行"""
        payload = {
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = self.session.post(f"{self.base_url}/ai/llm/completion", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return JobResult(
            job_id=data.get("job_id", ""),
            status=data.get("status", ""),
            result=data.get("result"),
            error=data.get("error")
        )
    
    def vision_analyze(self, image_url: str, task: str = "analyze", 
                      options: Optional[Dict[str, Any]] = None) -> JobResult:
        """画像解析実行"""
        payload = {
            "image_url": image_url,
            "task": task,
            "options": options or {}
        }
        
        response = self.session.post(f"{self.base_url}/ai/vision/analyze", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return JobResult(
            job_id=data.get("job_id", ""),
            status=data.get("status", ""),
            result=data.get("result"),
            error=data.get("error")
        )
    
    def process_data(self, operation: str, data: Dict[str, Any], 
                    options: Optional[Dict[str, Any]] = None) -> JobResult:
        """データ処理実行"""
        payload = {
            "operation": operation,
            "data": data,
            "options": options or {}
        }
        
        response = self.session.post(f"{self.base_url}/data/process", json=payload)
        response.raise_for_status()
        result_data = response.json()
        
        return JobResult(
            job_id="data-" + str(hash(json.dumps(payload))),
            status=result_data.get("status", ""),
            result=result_data.get("result"),
            error=result_data.get("error")
        )
    
    def get_job_status(self, job_id: str) -> JobResult:
        """ジョブ状態取得"""
        response = self.session.get(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        data = response.json()
        
        return JobResult(
            job_id=data.get("job_id", job_id),
            status=data.get("status", ""),
            result=data.get("result"),
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )
    
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """ファイルアップロード"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.session.post(f"{self.base_url}/data/upload", files=files)
        
        response.raise_for_status()
        return response.json()

# 使用例
if __name__ == "__main__":
    # SDK初期化
    sdk = AiSembleSDK()
    
    # ヘルスチェック
    health = sdk.health()
    print(f"Platform status: {health['status']}")
    
    # LLM推論
    llm_result = sdk.llm_completion(
        prompt="Pythonでファイルを読み込む方法を教えてください",
        max_tokens=200,
        temperature=0.5
    )
    print(f"LLM Result: {llm_result.result}")
    
    # データ処理
    data_result = sdk.process_data(
        operation="analyze",
        data={
            "records": [
                {"name": "Alice", "score": 85},
                {"name": "Bob", "score": 92}
            ]
        }
    )
    print(f"Data Analysis: {data_result.result}")
```

これらの例により、Ai-semble v2の具体的な使用イメージと実装方法が明確になります。