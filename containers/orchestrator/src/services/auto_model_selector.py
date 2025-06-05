"""
自動モデル選択サービス
タスクやコンテンツに応じて最適なAIモデルを自動選択
"""
import re
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import structlog

from .model_registry import get_model_registry

logger = structlog.get_logger()

@dataclass
class ModelSelection:
    """モデル選択結果"""
    model_name: str
    confidence: float
    reason: str
    fallback_models: List[str]

class AutoModelSelector:
    """タスクに応じた自動モデル選択"""
    
    def __init__(self):
        self.registry = get_model_registry()
        
        # タスクパターンマッチング (日本語・英語対応)
        self.task_patterns = {
            'code': [
                r'コード', r'プログラム', r'関数', r'クラス', r'実装', r'デバッグ',
                r'class\s+\w+', r'def\s+\w+', r'function\s+\w+', r'import\s+\w+',
                r'var\s+\w+', r'const\s+\w+', r'let\s+\w+', r'#include',
                r'code', r'program', r'function', r'debug', r'implement'
            ],
            'medical': [
                r'診断', r'症状', r'医療', r'薬', r'治療', r'病気', r'疾患',
                r'diagnosis', r'symptom', r'medical', r'medicine', r'treatment',
                r'disease', r'patient', r'clinical', r'therapy'
            ],
            'legal': [
                r'法律', r'契約', r'規則', r'条項', r'規制', r'判例',
                r'law', r'legal', r'contract', r'regulation', r'clause',
                r'statute', r'court', r'judgment'
            ],
            'creative': [
                r'物語', r'詩', r'小説', r'創作', r'キャラクター', r'ストーリー',
                r'story', r'novel', r'creative', r'character', r'plot',
                r'fiction', r'narrative', r'poem', r'poetry'
            ],
            'math': [
                r'計算', r'数式', r'数学', r'微分', r'積分', r'行列', r'統計',
                r'math', r'calculation', r'equation', r'formula', r'derivative',
                r'integral', r'matrix', r'statistics', r'\d+\s*[+\-*/]\s*\d+'
            ],
            'japanese': [
                r'[ひらがな]', r'[カタカナ]', r'[漢字]', r'です', r'ます', r'である',
                r'について', r'に関して', r'を行う', r'を実施'
            ],
            'translation': [
                r'翻訳', r'translate', r'英訳', r'和訳', r'中国語', r'韓国語',
                r'English', r'Japanese', r'Chinese', r'Korean'
            ]
        }
        
        # 性能・コスト・品質マトリックス
        self.model_metrics = {
            'gpt-4': {'performance': 0.95, 'cost': 0.2, 'quality': 0.98},
            'gpt-3.5-turbo': {'performance': 0.85, 'cost': 0.8, 'quality': 0.90},
            'llama2-7b': {'performance': 0.75, 'cost': 0.95, 'quality': 0.80},
            'japanese-stablelm': {'performance': 0.70, 'cost': 0.90, 'quality': 0.85},
            'code-llama': {'performance': 0.80, 'cost': 0.90, 'quality': 0.88},
            'biobert': {'performance': 0.85, 'cost': 0.85, 'quality': 0.92}
        }
    
    def select_optimal_model(self, 
                           request: Dict[str, Any], 
                           task_type: str = "llm",
                           priority: str = "balanced") -> ModelSelection:
        """最適なモデルを自動選択"""
        prompt = request.get('prompt', request.get('text', ''))
        max_tokens = request.get('max_tokens', 100)
        
        # タスク分類
        detected_tasks = self._classify_tasks(prompt)
        primary_task = detected_tasks[0] if detected_tasks else 'general'
        
        logger.info("task_classification_result",
                   primary_task=primary_task,
                   all_detected=detected_tasks,
                   prompt_length=len(prompt))
        
        # モデル選択ロジック
        selection = self._select_model_by_task(
            primary_task, request, priority, detected_tasks
        )
        
        # フォールバック候補生成
        fallback_models = self._generate_fallback_models(
            selection.model_name, primary_task, task_type
        )
        selection.fallback_models = fallback_models
        
        logger.info("model_selection_completed",
                   selected_model=selection.model_name,
                   confidence=selection.confidence,
                   reason=selection.reason,
                   fallbacks=fallback_models)
        
        return selection
    
    def _classify_tasks(self, text: str) -> List[str]:
        """テキストからタスクを分類（複数タスク対応）"""
        text_lower = text.lower()
        detected_tasks = []
        task_scores = {}
        
        for task, patterns in self.task_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            if score > 0:
                task_scores[task] = score
        
        # スコア順にソート
        sorted_tasks = sorted(task_scores.items(), key=lambda x: x[1], reverse=True)
        detected_tasks = [task for task, score in sorted_tasks if score > 0]
        
        return detected_tasks if detected_tasks else ['general']
    
    def _select_model_by_task(self, 
                            primary_task: str, 
                            request: Dict[str, Any],
                            priority: str,
                            all_tasks: List[str]) -> ModelSelection:
        """タスクベースのモデル選択"""
        
        if primary_task == 'code':
            return self._select_code_model(request, priority)
        elif primary_task == 'medical':
            return self._select_medical_model(request, priority)
        elif primary_task == 'legal':
            return self._select_legal_model(request, priority)
        elif primary_task == 'creative':
            return self._select_creative_model(request, priority)
        elif primary_task == 'math':
            return self._select_math_model(request, priority)
        elif primary_task == 'japanese':
            return self._select_japanese_model(request, priority)
        elif primary_task == 'translation':
            return self._select_translation_model(request, priority)
        else:
            return self._select_general_model(request, priority)
    
    def _select_code_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """コード生成に最適なモデル選択"""
        available = self.registry.list_available_models()
        
        if priority == "quality":
            # 品質優先: GPT-4 > Code Llama > GPT-3.5
            if self._is_model_available('gpt-4', available):
                return ModelSelection(
                    model_name='gpt-4',
                    confidence=0.95,
                    reason="High-quality code generation with GPT-4",
                    fallback_models=[]
                )
        
        if priority == "cost" or priority == "balanced":
            # コスト効率: Code Llama > GPT-3.5 > GPT-4
            if self._is_model_available('code-llama', available):
                return ModelSelection(
                    model_name='code-llama',
                    confidence=0.88,
                    reason="Cost-efficient specialized code model",
                    fallback_models=[]
                )
        
        # フォールバック
        if self._is_model_available('gpt-3.5-turbo', available):
            return ModelSelection(
                model_name='gpt-3.5-turbo',
                confidence=0.80,
                reason="General purpose model for code generation",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_medical_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """医療タスクに最適なモデル選択"""
        available = self.registry.list_available_models()
        
        # 専門モデル優先
        if self._is_model_available('biobert', available):
            return ModelSelection(
                model_name='biobert',
                confidence=0.92,
                reason="Specialized medical domain model",
                fallback_models=[]
            )
        
        # 高性能汎用モデル
        if self._is_model_available('gpt-4', available):
            return ModelSelection(
                model_name='gpt-4',
                confidence=0.85,
                reason="High-quality general model for medical tasks",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_legal_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """法律タスクに最適なモデル選択"""
        available = self.registry.list_available_models()
        
        # 法律専門モデルがあれば使用
        if self._is_model_available('legalbert', available):
            return ModelSelection(
                model_name='legalbert',
                confidence=0.90,
                reason="Specialized legal domain model",
                fallback_models=[]
            )
        
        # 高品質汎用モデル
        if self._is_model_available('gpt-4', available):
            return ModelSelection(
                model_name='gpt-4',
                confidence=0.82,
                reason="High-quality model for legal reasoning",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_creative_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """創作タスクに最適なモデル選択"""
        max_tokens = request.get('max_tokens', 100)
        
        available = self.registry.list_available_models()
        
        # 長文生成には高性能モデル
        if max_tokens > 500:
            if self._is_model_available('gpt-4', available):
                return ModelSelection(
                    model_name='gpt-4',
                    confidence=0.90,
                    reason="High-quality model for long-form creative writing",
                    fallback_models=[]
                )
        
        # 短・中文は効率重視
        if self._is_model_available('gpt-3.5-turbo', available):
            return ModelSelection(
                model_name='gpt-3.5-turbo',
                confidence=0.85,
                reason="Balanced model for creative tasks",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_math_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """数学タスクに最適なモデル選択"""
        available = self.registry.list_available_models()
        
        # 数学には高精度モデル
        if self._is_model_available('gpt-4', available):
            return ModelSelection(
                model_name='gpt-4',
                confidence=0.88,
                reason="High-accuracy model for mathematical reasoning",
                fallback_models=[]
            )
        
        if self._is_model_available('gpt-3.5-turbo', available):
            return ModelSelection(
                model_name='gpt-3.5-turbo',
                confidence=0.80,
                reason="General model for basic math tasks",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_japanese_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """日本語タスクに最適なモデル選択"""
        available = self.registry.list_available_models()
        
        # 日本語特化モデル優先
        if self._is_model_available('japanese-stablelm', available):
            return ModelSelection(
                model_name='japanese-stablelm',
                confidence=0.85,
                reason="Japanese language specialized model",
                fallback_models=[]
            )
        
        # 多言語対応モデル
        if self._is_model_available('gpt-4', available):
            return ModelSelection(
                model_name='gpt-4',
                confidence=0.80,
                reason="Multilingual model with Japanese support",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_translation_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """翻訳タスクに最適なモデル選択"""
        available = self.registry.list_available_models()
        
        # 翻訳には多言語対応の高性能モデル
        if self._is_model_available('gpt-4', available):
            return ModelSelection(
                model_name='gpt-4',
                confidence=0.90,
                reason="High-quality multilingual translation model",
                fallback_models=[]
            )
        
        if self._is_model_available('gpt-3.5-turbo', available):
            return ModelSelection(
                model_name='gpt-3.5-turbo',
                confidence=0.82,
                reason="General multilingual model for translation",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _select_general_model(self, request: Dict[str, Any], priority: str) -> ModelSelection:
        """一般タスク用モデル選択"""
        max_tokens = request.get('max_tokens', 100)
        available = self.registry.list_available_models()
        
        if priority == "cost":
            # コスト重視
            if max_tokens <= 100 and self._is_model_available('llama2-7b', available):
                return ModelSelection(
                    model_name='llama2-7b',
                    confidence=0.75,
                    reason="Cost-efficient local model for short tasks",
                    fallback_models=[]
                )
        
        if priority == "quality":
            # 品質重視
            if self._is_model_available('gpt-4', available):
                return ModelSelection(
                    model_name='gpt-4',
                    confidence=0.88,
                    reason="Highest quality general-purpose model",
                    fallback_models=[]
                )
        
        # バランス重視（デフォルト）
        if self._is_model_available('gpt-3.5-turbo', available):
            return ModelSelection(
                model_name='gpt-3.5-turbo',
                confidence=0.85,
                reason="Balanced performance and cost for general tasks",
                fallback_models=[]
            )
        
        return self._get_default_fallback()
    
    def _is_model_available(self, model_name: str, available_models: Dict[str, Any]) -> bool:
        """モデルが利用可能かチェック"""
        for category in available_models.values():
            if isinstance(category, dict) and model_name in category:
                return True
        return False
    
    def _generate_fallback_models(self, 
                                selected_model: str, 
                                task: str, 
                                task_type: str) -> List[str]:
        """フォールバックモデル候補生成"""
        fallbacks = []
        
        # タスク別フォールバック戦略
        if task == 'code':
            fallbacks = ['gpt-4', 'gpt-3.5-turbo', 'llama2-7b']
        elif task == 'medical':
            fallbacks = ['gpt-4', 'gpt-3.5-turbo', 'biobert']
        elif task == 'japanese':
            fallbacks = ['gpt-4', 'gpt-3.5-turbo', 'japanese-stablelm']
        else:
            fallbacks = ['gpt-4', 'gpt-3.5-turbo', 'llama2-7b']
        
        # 選択されたモデルを除外
        fallbacks = [m for m in fallbacks if m != selected_model]
        
        # 利用可能性をチェック
        available = self.registry.list_available_models()
        available_fallbacks = []
        for model in fallbacks:
            if self._is_model_available(model, available):
                available_fallbacks.append(model)
        
        return available_fallbacks[:3]  # 最大3つまで
    
    def _get_default_fallback(self) -> ModelSelection:
        """デフォルトフォールバック"""
        return ModelSelection(
            model_name='gpt-3.5-turbo',
            confidence=0.60,
            reason="Default fallback model",
            fallback_models=['llama2-7b']
        )
    
    def get_selection_explanation(self, selection: ModelSelection) -> Dict[str, Any]:
        """選択理由の詳細説明を生成"""
        model_info = self.registry.get_model_info(selection.model_name)
        metrics = self.model_metrics.get(selection.model_name, {})
        
        return {
            "selected_model": selection.model_name,
            "confidence": selection.confidence,
            "reason": selection.reason,
            "model_info": model_info,
            "performance_metrics": metrics,
            "fallback_options": selection.fallback_models,
            "recommendation": self._generate_recommendation(selection, metrics)
        }
    
    def _generate_recommendation(self, 
                               selection: ModelSelection, 
                               metrics: Dict[str, float]) -> str:
        """選択に対する推奨事項を生成"""
        if selection.confidence > 0.9:
            return "Excellent match for this task type"
        elif selection.confidence > 0.8:
            return "Good match with high confidence"
        elif selection.confidence > 0.7:
            return "Reasonable choice, consider fallback options if needed"
        else:
            return "Conservative choice, monitor performance and consider alternatives"

# グローバルインスタンス
_auto_selector = None

def get_auto_model_selector() -> AutoModelSelector:
    """自動モデル選択のシングルトンインスタンスを取得"""
    global _auto_selector
    if _auto_selector is None:
        _auto_selector = AutoModelSelector()
    return _auto_selector