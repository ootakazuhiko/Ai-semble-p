"""
AIモデル管理レジストリ
動的なモデル管理と設定を提供
"""
import yaml
import json
import aiofiles
from typing import Dict, Any, Optional, List
from pathlib import Path
import structlog

logger = structlog.get_logger()

class ModelRegistry:
    """AIモデル管理レジストリ"""
    
    def __init__(self, config_path: str = "/config/models.yaml"):
        self.config_path = Path(config_path)
        self.models: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """モデル設定を読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.models = yaml.safe_load(f) or {}
                logger.info("model_config_loaded", 
                           config_path=str(self.config_path),
                           model_count=len(self.models))
            else:
                # デフォルト設定を作成
                self.models = self._get_default_config()
                self._save_config()
                logger.info("default_model_config_created")
        except Exception as e:
            logger.error("failed_to_load_model_config", error=str(e))
            self.models = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルトモデル設定"""
        return {
            "llm_models": {
                "gpt-3.5-turbo": {
                    "provider": "openai",
                    "endpoint": "https://api.openai.com/v1/chat/completions",
                    "max_tokens": 4096,
                    "cost_per_token": 0.002,
                    "task": "llm",
                    "capabilities": ["text_generation", "chat", "code_generation"]
                },
                "llama2-7b": {
                    "provider": "huggingface",
                    "model_id": "meta-llama/Llama-2-7b-chat-hf",
                    "device": "cuda",
                    "quantization": "4bit",
                    "task": "llm",
                    "capabilities": ["text_generation", "chat"]
                },
                "japanese-stablelm": {
                    "provider": "local",
                    "model_path": "/models/japanese-stablelm-base-alpha-7b",
                    "tokenizer_path": "/models/japanese-stablelm-tokenizer",
                    "task": "llm",
                    "language": "ja",
                    "capabilities": ["text_generation"]
                }
            },
            "vision_models": {
                "yolo-v8": {
                    "provider": "ultralytics",
                    "model_id": "yolov8n.pt",
                    "task": "object_detection",
                    "capabilities": ["object_detection", "bbox_prediction"]
                },
                "sam": {
                    "provider": "local",
                    "model_path": "/models/sam_vit_h_4b8939.pth",
                    "task": "segmentation",
                    "capabilities": ["image_segmentation", "mask_generation"]
                },
                "stable-diffusion": {
                    "provider": "diffusers",
                    "model_id": "runwayml/stable-diffusion-v1-5",
                    "task": "image_generation",
                    "capabilities": ["text_to_image", "image_generation"]
                }
            },
            "nlp_models": {
                "bert-base": {
                    "provider": "huggingface",
                    "model_id": "bert-base-uncased",
                    "task": "classification",
                    "capabilities": ["text_classification", "sentiment_analysis"]
                },
                "biobert": {
                    "provider": "huggingface",
                    "model_id": "dmis-lab/biobert-base-cased-v1.1",
                    "domain": "medical",
                    "task": "classification",
                    "capabilities": ["medical_ner", "medical_classification"]
                }
            }
        }
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """モデル情報を取得"""
        # 全カテゴリを検索
        for category in self.models.values():
            if isinstance(category, dict) and model_name in category:
                model_info = category[model_name].copy()
                model_info["model_name"] = model_name
                return model_info
        
        logger.warning("model_not_found", model_name=model_name)
        return None
    
    def list_available_models(self, task: str = None, provider: str = None) -> Dict[str, Any]:
        """利用可能なモデル一覧を取得"""
        result = {}
        
        for category_name, category_models in self.models.items():
            if not isinstance(category_models, dict):
                continue
                
            filtered_models = {}
            for model_name, model_info in category_models.items():
                # タスクフィルタ
                if task and model_info.get('task') != task:
                    continue
                
                # プロバイダーフィルタ
                if provider and model_info.get('provider') != provider:
                    continue
                
                filtered_models[model_name] = model_info
            
            if filtered_models:
                result[category_name] = filtered_models
        
        return result
    
    def list_models_by_capability(self, capability: str) -> List[str]:
        """特定の能力を持つモデル一覧"""
        matching_models = []
        
        for category_models in self.models.values():
            if not isinstance(category_models, dict):
                continue
                
            for model_name, model_info in category_models.items():
                capabilities = model_info.get('capabilities', [])
                if capability in capabilities:
                    matching_models.append(model_name)
        
        return matching_models
    
    def register_model(self, category: str, model_name: str, model_info: Dict[str, Any]) -> bool:
        """新しいモデルを登録"""
        try:
            if category not in self.models:
                self.models[category] = {}
            
            self.models[category][model_name] = model_info
            self._save_config()
            
            logger.info("model_registered",
                       category=category,
                       model_name=model_name)
            return True
            
        except Exception as e:
            logger.error("failed_to_register_model",
                        category=category,
                        model_name=model_name,
                        error=str(e))
            return False
    
    def update_model(self, model_name: str, updates: Dict[str, Any]) -> bool:
        """モデル情報を更新"""
        model_info = self.get_model_info(model_name)
        if not model_info:
            return False
        
        try:
            # 該当モデルを見つけて更新
            for category_models in self.models.values():
                if isinstance(category_models, dict) and model_name in category_models:
                    category_models[model_name].update(updates)
                    self._save_config()
                    
                    logger.info("model_updated",
                               model_name=model_name,
                               updates=list(updates.keys()))
                    return True
            
            return False
            
        except Exception as e:
            logger.error("failed_to_update_model",
                        model_name=model_name,
                        error=str(e))
            return False
    
    def remove_model(self, model_name: str) -> bool:
        """モデルを削除"""
        try:
            for category_models in self.models.values():
                if isinstance(category_models, dict) and model_name in category_models:
                    del category_models[model_name]
                    self._save_config()
                    
                    logger.info("model_removed", model_name=model_name)
                    return True
            
            logger.warning("model_not_found_for_removal", model_name=model_name)
            return False
            
        except Exception as e:
            logger.error("failed_to_remove_model",
                        model_name=model_name,
                        error=str(e))
            return False
    
    def get_model_stats(self) -> Dict[str, Any]:
        """モデル統計情報を取得"""
        stats = {
            "total_models": 0,
            "categories": {},
            "providers": {},
            "tasks": {}
        }
        
        for category_name, category_models in self.models.items():
            if not isinstance(category_models, dict):
                continue
                
            category_count = len(category_models)
            stats["total_models"] += category_count
            stats["categories"][category_name] = category_count
            
            for model_info in category_models.values():
                # プロバイダー統計
                provider = model_info.get('provider', 'unknown')
                stats["providers"][provider] = stats["providers"].get(provider, 0) + 1
                
                # タスク統計
                task = model_info.get('task', 'unknown')
                stats["tasks"][task] = stats["tasks"].get(task, 0) + 1
        
        return stats
    
    def _save_config(self) -> None:
        """設定をファイルに保存"""
        try:
            # ディレクトリが存在しない場合は作成
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.models, f, default_flow_style=False, allow_unicode=True)
                
            logger.debug("model_config_saved", config_path=str(self.config_path))
            
        except Exception as e:
            logger.error("failed_to_save_model_config", error=str(e))
    
    async def reload_config(self) -> bool:
        """設定をリロード"""
        try:
            self._load_config()
            logger.info("model_config_reloaded")
            return True
        except Exception as e:
            logger.error("failed_to_reload_config", error=str(e))
            return False

# グローバルインスタンス
_model_registry = None

def get_model_registry() -> ModelRegistry:
    """モデルレジストリのシングルトンインスタンスを取得"""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry