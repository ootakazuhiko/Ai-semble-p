# Ai-semble v2 高度なAIモデル統合ガイド

## 🎯 概要

このドキュメントは、Ai-semble v2における高度なAIモデル統合機能について説明します。

## 🧠 対応AIモデル拡張

### 1. 大規模言語モデル (LLM)

#### 対応モデル
- **GPT系**: GPT-3.5, GPT-4 (OpenAI API)
- **Llama系**: Llama 2, Code Llama (Hugging Face)
- **日本語特化**: Japanese StableLM, ELYZA (ローカル)
- **コード生成**: CodeT5, StarCoder (Hugging Face)

#### モデル切り替え機能
```python
# 動的モデル切り替え
@router.post("/ai/llm/completion/{model_name}")
async def llm_completion_with_model(model_name: str, request: LLMRequest):
    # モデル固有の処理
    if model_name == "gpt-4":
        return await process_openai_request(request)
    elif model_name == "llama2":
        return await process_llama_request(request)
    elif model_name == "japanese-stablelm":
        return await process_japanese_request(request)
```

### 2. 画像・ビジョンモデル

#### 対応タスク拡張
- **物体検出**: YOLO v8, DETR
- **セグメンテーション**: Segment Anything Model (SAM)
- **画像生成**: Stable Diffusion, DALL-E
- **光学文字認識**: PaddleOCR, TrOCR
- **医療画像**: MedSAM, ChestX-ray分析

#### マルチモーダル対応
```python
# 画像+テキストの統合分析
@router.post("/ai/multimodal/analyze")
async def multimodal_analyze(request: MultimodalRequest):
    vision_result = await analyze_image(request.image)
    text_context = await process_text(request.description)
    
    # 統合分析
    integrated_result = await combine_modalities(vision_result, text_context)
    return integrated_result
```

### 3. 自然言語処理強化

#### 専門分野対応
- **医療NLP**: BioBERT, ClinicalBERT
- **法律NLP**: LegalBERT
- **金融NLP**: FinBERT
- **多言語**: mBERT, XLM-R

#### カスタムモデル統合
```python
# ドメイン固有モデル
class DomainSpecificNLP:
    def __init__(self, domain: str):
        self.domain = domain
        self.model = self.load_domain_model(domain)
    
    def load_domain_model(self, domain: str):
        model_mapping = {
            "medical": "emilyalsentzer/Bio_ClinicalBERT",
            "legal": "nlpaueb/legal-bert-base-uncased",
            "financial": "ProsusAI/finbert"
        }
        return AutoModel.from_pretrained(model_mapping[domain])
```

## 🔧 モデル管理システム

### モデルレジストリ
```python
# containers/orchestrator/src/services/model_registry.py
from typing import Dict, Any, Optional
import yaml

class ModelRegistry:
    """AIモデル管理レジストリ"""
    
    def __init__(self, config_path: str = "/config/models.yaml"):
        self.config_path = config_path
        self.models = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """モデル設定を読み込み"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """モデル情報を取得"""
        return self.models.get(model_name)
    
    def list_available_models(self, task: str = None) -> Dict[str, Any]:
        """利用可能なモデル一覧"""
        if task:
            return {k: v for k, v in self.models.items() 
                   if v.get('task') == task}
        return self.models
    
    def register_model(self, model_name: str, model_info: Dict[str, Any]):
        """新しいモデルを登録"""
        self.models[model_name] = model_info
        self._save_config()
    
    def _save_config(self):
        """設定を保存"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.models, f)
```

### モデル設定ファイル
```yaml
# configs/models.yaml
llm_models:
  gpt-3.5-turbo:
    provider: openai
    endpoint: https://api.openai.com/v1/chat/completions
    max_tokens: 4096
    cost_per_token: 0.002
    
  llama2-7b:
    provider: huggingface
    model_id: meta-llama/Llama-2-7b-chat-hf
    device: cuda
    quantization: 4bit
    
  japanese-stablelm:
    provider: local
    model_path: /models/japanese-stablelm-base-alpha-7b
    tokenizer_path: /models/japanese-stablelm-tokenizer
    
vision_models:
  yolo-v8:
    provider: ultralytics
    model_id: yolov8n.pt
    task: object_detection
    
  sam:
    provider: local
    model_path: /models/sam_vit_h_4b8939.pth
    task: segmentation
    
  stable-diffusion:
    provider: diffusers
    model_id: runwayml/stable-diffusion-v1-5
    task: image_generation

nlp_models:
  bert-base:
    provider: huggingface
    model_id: bert-base-uncased
    task: classification
    
  biobert:
    provider: huggingface
    model_id: dmis-lab/biobert-base-cased-v1.1
    domain: medical
```

## 🚀 高度な機能実装

### 1. モデルアンサンブル
```python
# containers/orchestrator/src/services/ensemble.py
import asyncio
from typing import List, Dict, Any
import numpy as np

class ModelEnsemble:
    """複数モデルのアンサンブル処理"""
    
    def __init__(self, models: List[str], weights: List[float] = None):
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)
    
    async def ensemble_prediction(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """アンサンブル予測実行"""
        # 各モデルで並列実行
        tasks = [self._single_model_prediction(model, request) 
                for model in self.models]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 有効な結果のみフィルタ
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        if not valid_results:
            raise RuntimeError("All ensemble models failed")
        
        # 結果を統合
        return self._combine_results(valid_results)
    
    async def _single_model_prediction(self, model: str, request: Dict[str, Any]):
        """単一モデル予測"""
        # モデル固有のAPI呼び出し
        connection_pool = await get_connection_pool()
        response = await connection_pool.post(
            f"/ai/llm/completion/{model}",
            json=request
        )
        return response.json()
    
    def _combine_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """結果統合（重み付き平均等）"""
        if len(results) == 1:
            return results[0]
        
        # 信頼度スコアベースの統合
        combined_text = ""
        total_confidence = 0
        
        for i, result in enumerate(results):
            weight = self.weights[i] if i < len(self.weights) else 1.0
            confidence = result.get('confidence', 0.5) * weight
            
            if confidence > total_confidence:
                combined_text = result.get('result', '')
                total_confidence = confidence
        
        return {
            "result": combined_text,
            "confidence": total_confidence,
            "ensemble_size": len(results),
            "method": "weighted_confidence"
        }
```

### 2. 自動モデル選択
```python
# containers/orchestrator/src/services/auto_model_selector.py
import re
from typing import Dict, Any, Optional

class AutoModelSelector:
    """タスクに応じた自動モデル選択"""
    
    def __init__(self, model_registry):
        self.registry = model_registry
        
        # タスクパターンマッチング
        self.task_patterns = {
            'code': [r'コード', r'プログラム', r'関数', r'class', r'def ', r'import '],
            'medical': [r'診断', r'症状', r'医療', r'薬', r'治療'],
            'legal': [r'法律', r'契約', r'規則', r'条項'],
            'creative': [r'物語', r'詩', r'小説', r'創作'],
            'math': [r'計算', r'数式', r'=', r'\+', r'\*', r'微分', r'積分']
        }
    
    def select_optimal_model(self, 
                           request: Dict[str, Any], 
                           task_type: str = "llm") -> str:
        """最適なモデルを自動選択"""
        prompt = request.get('prompt', '')
        
        # タスク分類
        detected_task = self._classify_task(prompt)
        
        # モデル選択ロジック
        if detected_task == 'code':
            return self._select_code_model(request)
        elif detected_task == 'medical':
            return self._select_medical_model(request)
        elif detected_task == 'creative':
            return self._select_creative_model(request)
        else:
            return self._select_general_model(request)
    
    def _classify_task(self, text: str) -> str:
        """テキストからタスクを分類"""
        text_lower = text.lower()
        
        for task, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return task
        
        return 'general'
    
    def _select_code_model(self, request: Dict[str, Any]) -> str:
        """コード生成に最適なモデル選択"""
        available = self.registry.list_available_models('llm')
        
        # Code特化モデル優先
        if 'code-llama' in available:
            return 'code-llama'
        elif 'starcoder' in available:
            return 'starcoder'
        else:
            return 'gpt-3.5-turbo'  # フォールバック
    
    def _select_medical_model(self, request: Dict[str, Any]) -> str:
        """医療タスクに最適なモデル選択"""
        # 専門モデルが利用可能かチェック
        if 'biobert' in self.registry.models:
            return 'biobert'
        return 'gpt-4'  # 医療には高性能モデル
    
    def _select_creative_model(self, request: Dict[str, Any]) -> str:
        """創作タスクに最適なモデル選択"""
        max_tokens = request.get('max_tokens', 100)
        
        # 長文生成には大規模モデル
        if max_tokens > 500:
            return 'gpt-4'
        else:
            return 'gpt-3.5-turbo'
    
    def _select_general_model(self, request: Dict[str, Any]) -> str:
        """一般タスク用モデル選択"""
        # コスト効率を考慮
        max_tokens = request.get('max_tokens', 100)
        
        if max_tokens <= 100:
            return 'gpt-3.5-turbo'  # 短文は効率重視
        else:
            return 'llama2-7b'  # 長文はローカルモデル
```

### 3. カスタムファインチューニング支援
```python
# containers/ai-services/llm/src/fine_tuning.py
import torch
from transformers import Trainer, TrainingArguments
from typing import Dict, Any, List
import json

class FineTuningService:
    """カスタムモデルファインチューニング"""
    
    def __init__(self, base_model: str = "llama2-7b"):
        self.base_model = base_model
        self.model = None
        self.tokenizer = None
    
    async def prepare_training_data(self, 
                                  training_examples: List[Dict[str, str]]) -> Dict[str, Any]:
        """訓練データの準備"""
        formatted_data = []
        
        for example in training_examples:
            # 対話形式のデータ整形
            formatted_example = {
                "input": example["prompt"],
                "output": example["response"]
            }
            formatted_data.append(formatted_example)
        
        return {
            "training_data": formatted_data,
            "data_size": len(formatted_data),
            "status": "prepared"
        }
    
    async def start_fine_tuning(self, 
                              training_data: List[Dict[str, str]],
                              hyperparameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """ファインチューニング開始"""
        default_params = {
            "learning_rate": 2e-5,
            "num_epochs": 3,
            "batch_size": 4,
            "max_length": 512
        }
        
        params = {**default_params, **(hyperparameters or {})}
        
        # 非同期でファインチューニング実行
        training_job_id = f"ft_{int(time.time())}"
        
        # 実際のファインチューニングは別プロセスで実行
        # (実装簡略化のため、ここではステータス返却のみ)
        
        return {
            "job_id": training_job_id,
            "status": "started",
            "parameters": params,
            "estimated_time": len(training_data) * params["num_epochs"] * 0.1
        }
    
    async def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """ファインチューニング状況確認"""
        # 実際の実装では訓練状況を確認
        return {
            "job_id": job_id,
            "status": "in_progress",
            "progress": 0.65,
            "current_epoch": 2,
            "total_epochs": 3,
            "current_loss": 0.234
        }
```

### 4. プラグイン式モデル統合
```python
# containers/orchestrator/src/plugins/base_plugin.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AIModelPlugin(ABC):
    """AIモデルプラグインのベースクラス"""
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """プラグイン初期化"""
        pass
    
    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """リクエスト処理"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報取得"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """リソース解放"""
        pass

# 具体的プラグイン例
class OpenAIPlugin(AIModelPlugin):
    """OpenAI GPT プラグイン"""
    
    def __init__(self):
        self.client = None
        self.api_key = None
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """OpenAI API初期化"""
        self.api_key = config.get('api_key')
        if not self.api_key:
            return False
        
        import openai
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        return True
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI API呼び出し"""
        response = await self.client.chat.completions.create(
            model=request.get('model', 'gpt-3.5-turbo'),
            messages=[{"role": "user", "content": request['prompt']}],
            max_tokens=request.get('max_tokens', 150),
            temperature=request.get('temperature', 0.7)
        )
        
        return {
            "result": response.choices[0].message.content,
            "usage": response.usage.dict(),
            "model": response.model
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            "capabilities": ["text_generation", "chat", "code_generation"]
        }
    
    async def cleanup(self):
        """クリーンアップ"""
        if self.client:
            await self.client.close()
```

## 📊 パフォーマンス比較

### モデル選択指標
| モデル | レスポンス時間 | 精度 | コスト | 推奨用途 |
|--------|----------------|------|--------|----------|
| GPT-4 | 3-8秒 | 最高 | 高 | 複雑なタスク |
| GPT-3.5 | 1-3秒 | 高 | 中 | 一般的なタスク |
| Llama2-7B | 0.5-2秒 | 中 | 低 | ローカル処理 |
| CodeLlama | 0.8-2.5秒 | 高(コード) | 低 | プログラミング |

### 最適化戦略
1. **キャッシュ活用**: 同一リクエストの結果キャッシュ
2. **モデル分散**: 負荷に応じたモデル分散配置
3. **プリローディング**: よく使用されるモデルの事前読み込み
4. **量子化**: メモリ使用量削減のためのモデル量子化

このように、Ai-semble v2は多様なAIモデルを統合し、タスクに応じた最適な選択を自動化できる高度なプラットフォームとなります。