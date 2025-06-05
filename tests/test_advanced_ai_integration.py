"""
高度なAIモデル統合機能のテスト
"""
import pytest
import asyncio
import json
from pathlib import Path
import tempfile
import yaml

from containers.orchestrator.src.services.model_registry import ModelRegistry
from containers.orchestrator.src.services.auto_model_selector import AutoModelSelector


class TestModelRegistry:
    """モデルレジストリのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        # 一時的な設定ファイルを作成
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_models.yaml"
        self.registry = ModelRegistry(str(self.config_path))
    
    def test_load_default_config(self):
        """デフォルト設定の読み込みテスト"""
        assert self.registry.models is not None
        assert "llm_models" in self.registry.models
        assert "gpt-3.5-turbo" in self.registry.models["llm_models"]
    
    def test_get_model_info(self):
        """モデル情報取得テスト"""
        model_info = self.registry.get_model_info("gpt-3.5-turbo")
        assert model_info is not None
        assert model_info["provider"] == "openai"
        assert "text_generation" in model_info["capabilities"]
        
        # 存在しないモデル
        none_info = self.registry.get_model_info("nonexistent-model")
        assert none_info is None
    
    def test_list_available_models(self):
        """利用可能なモデル一覧テスト"""
        # 全モデル
        all_models = self.registry.list_available_models()
        assert len(all_models) > 0
        
        # タスクフィルタ
        llm_models = self.registry.list_available_models(task="llm")
        assert len(llm_models) > 0
        
        # プロバイダーフィルタ
        openai_models = self.registry.list_available_models(provider="openai")
        assert len(openai_models) > 0
    
    def test_register_model(self):
        """モデル登録テスト"""
        test_model_info = {
            "provider": "test",
            "task": "llm",
            "capabilities": ["test_capability"],
            "quality_score": 0.8
        }
        
        success = self.registry.register_model("test_models", "test-model", test_model_info)
        assert success is True
        
        # 登録確認
        registered_info = self.registry.get_model_info("test-model")
        assert registered_info is not None
        assert registered_info["provider"] == "test"
    
    def test_update_model(self):
        """モデル更新テスト"""
        updates = {"quality_score": 0.95, "new_field": "test_value"}
        success = self.registry.update_model("gpt-3.5-turbo", updates)
        assert success is True
        
        # 更新確認
        updated_info = self.registry.get_model_info("gpt-3.5-turbo")
        assert updated_info["quality_score"] == 0.95
        assert updated_info["new_field"] == "test_value"
    
    def test_remove_model(self):
        """モデル削除テスト"""
        # まず新しいモデルを登録
        test_model_info = {"provider": "test", "task": "test"}
        self.registry.register_model("test_models", "delete-me", test_model_info)
        
        # 削除実行
        success = self.registry.remove_model("delete-me")
        assert success is True
        
        # 削除確認
        deleted_info = self.registry.get_model_info("delete-me")
        assert deleted_info is None
    
    def test_list_models_by_capability(self):
        """能力別モデル一覧テスト"""
        text_gen_models = self.registry.list_models_by_capability("text_generation")
        assert len(text_gen_models) > 0
        assert "gpt-3.5-turbo" in text_gen_models
        
        # 存在しない能力
        empty_models = self.registry.list_models_by_capability("nonexistent_capability")
        assert len(empty_models) == 0
    
    def test_get_model_stats(self):
        """モデル統計取得テスト"""
        stats = self.registry.get_model_stats()
        
        assert "total_models" in stats
        assert "categories" in stats
        assert "providers" in stats
        assert "tasks" in stats
        assert stats["total_models"] > 0


class TestAutoModelSelector:
    """自動モデル選択のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.selector = AutoModelSelector()
    
    def test_classify_tasks(self):
        """タスク分類テスト"""
        # コード関連
        code_tasks = self.selector._classify_tasks("def hello(): print('hello world')")
        assert "code" in code_tasks
        
        # 日本語
        japanese_tasks = self.selector._classify_tasks("こんにちは、これは日本語のテストです。")
        assert "japanese" in japanese_tasks
        
        # 医療関連
        medical_tasks = self.selector._classify_tasks("patient diagnosis and treatment options")
        assert "medical" in medical_tasks
        
        # 数学関連
        math_tasks = self.selector._classify_tasks("calculate 2 + 2 * 3 = ?")
        assert "math" in math_tasks
    
    def test_select_optimal_model_code(self):
        """コード生成タスクのモデル選択テスト"""
        request = {
            "prompt": "def fibonacci(n): # complete this function",
            "max_tokens": 100
        }
        
        selection = self.selector.select_optimal_model(
            request, 
            task_type="llm",
            priority="quality"
        )
        
        assert selection.model_name is not None
        assert selection.confidence > 0
        assert "code" in selection.reason.lower() or "gpt" in selection.model_name.lower()
    
    def test_select_optimal_model_japanese(self):
        """日本語タスクのモデル選択テスト"""
        request = {
            "prompt": "日本の文化について説明してください。",
            "max_tokens": 200
        }
        
        selection = self.selector.select_optimal_model(
            request,
            task_type="llm",
            priority="balanced"
        )
        
        assert selection.model_name is not None
        assert selection.confidence > 0
    
    def test_select_optimal_model_medical(self):
        """医療タスクのモデル選択テスト"""
        request = {
            "prompt": "What are the symptoms of hypertension?",
            "max_tokens": 150
        }
        
        selection = self.selector.select_optimal_model(
            request,
            task_type="llm", 
            priority="quality"
        )
        
        assert selection.model_name is not None
        assert selection.confidence > 0
    
    def test_select_optimal_model_creative(self):
        """創作タスクのモデル選択テスト"""
        request = {
            "prompt": "Write a short story about a robot",
            "max_tokens": 500  # 長文
        }
        
        selection = self.selector.select_optimal_model(
            request,
            task_type="llm",
            priority="quality"
        )
        
        assert selection.model_name is not None
        assert selection.confidence > 0
        # 長文創作には高性能モデルが選ばれることを期待
        assert "gpt-4" in selection.model_name or selection.confidence > 0.8
    
    def test_select_optimal_model_cost_priority(self):
        """コスト優先モデル選択テスト"""
        request = {
            "prompt": "Simple text generation task",
            "max_tokens": 50
        }
        
        selection = self.selector.select_optimal_model(
            request,
            task_type="llm",
            priority="cost"
        )
        
        assert selection.model_name is not None
        assert selection.confidence > 0
        # コスト優先では効率的なモデルが選ばれることを期待
    
    def test_generate_fallback_models(self):
        """フォールバックモデル生成テスト"""
        fallbacks = self.selector._generate_fallback_models("gpt-4", "code", "llm")
        
        assert isinstance(fallbacks, list)
        assert "gpt-4" not in fallbacks  # 選択されたモデルは除外される
        assert len(fallbacks) <= 3  # 最大3つまで
    
    def test_get_selection_explanation(self):
        """選択理由説明テスト"""
        request = {
            "prompt": "test prompt",
            "max_tokens": 100
        }
        
        selection = self.selector.select_optimal_model(request)
        explanation = self.selector.get_selection_explanation(selection)
        
        assert "selected_model" in explanation
        assert "confidence" in explanation
        assert "reason" in explanation
        assert "recommendation" in explanation


class TestIntegrationScenarios:
    """統合シナリオテスト"""
    
    def setup_method(self):
        """セットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "integration_models.yaml"
        self.registry = ModelRegistry(str(self.config_path))
        self.selector = AutoModelSelector()
    
    def test_dynamic_model_registration_and_selection(self):
        """動的モデル登録と選択の統合テスト"""
        # 1. 新しい専用モデルを登録
        custom_model_info = {
            "provider": "custom",
            "task": "llm",
            "domain": "legal",
            "capabilities": ["legal_analysis", "contract_review"],
            "quality_score": 0.95,
            "speed_score": 0.80
        }
        
        success = self.registry.register_model("llm_models", "legal-expert", custom_model_info)
        assert success is True
        
        # 2. 法律関連タスクでモデル選択
        legal_request = {
            "prompt": "Review this contract clause for legal compliance",
            "max_tokens": 200
        }
        
        # レジストリを更新
        self.selector.registry = self.registry
        
        selection = self.selector.select_optimal_model(legal_request, priority="quality")
        
        # 3. 選択結果を確認
        assert selection.model_name is not None
        assert selection.confidence > 0
    
    def test_model_capability_based_selection(self):
        """能力ベースのモデル選択テスト"""
        # 特定の能力を持つモデル一覧を取得
        code_models = self.registry.list_models_by_capability("code_generation")
        
        if len(code_models) > 0:
            # コード生成タスクでモデル選択
            code_request = {
                "prompt": "Write a Python function to sort a list",
                "max_tokens": 150
            }
            
            selection = self.selector.select_optimal_model(code_request)
            
            # 選択されたモデルがコード生成能力を持つことを確認
            model_info = self.registry.get_model_info(selection.model_name)
            if model_info and "capabilities" in model_info:
                capabilities = model_info["capabilities"]
                # コード関連の能力を持っているか、一般的な高性能モデルかを確認
                assert (any("code" in cap for cap in capabilities) or 
                       selection.model_name in ["gpt-4", "gpt-3.5-turbo"])
    
    def test_multilingual_model_selection(self):
        """多言語モデル選択テスト"""
        # 日本語タスク
        japanese_request = {
            "prompt": "東京の観光スポットを教えてください",
            "max_tokens": 200
        }
        
        jp_selection = self.selector.select_optimal_model(japanese_request)
        
        # 英語タスク  
        english_request = {
            "prompt": "Explain machine learning concepts",
            "max_tokens": 200
        }
        
        en_selection = self.selector.select_optimal_model(english_request)
        
        # 両方で適切なモデルが選択されることを確認
        assert jp_selection.model_name is not None
        assert en_selection.model_name is not None
        assert jp_selection.confidence > 0
        assert en_selection.confidence > 0
    
    def test_performance_priority_scenarios(self):
        """パフォーマンス優先度シナリオテスト"""
        test_request = {
            "prompt": "General AI task for testing",
            "max_tokens": 100
        }
        
        # 品質優先
        quality_selection = self.selector.select_optimal_model(
            test_request, priority="quality"
        )
        
        # コスト優先
        cost_selection = self.selector.select_optimal_model(
            test_request, priority="cost"
        )
        
        # バランス重視
        balanced_selection = self.selector.select_optimal_model(
            test_request, priority="balanced"
        )
        
        # 全ての選択が成功することを確認
        assert quality_selection.model_name is not None
        assert cost_selection.model_name is not None
        assert balanced_selection.model_name is not None
        
        # 優先度による選択の違いを確認
        models = {quality_selection.model_name, cost_selection.model_name, balanced_selection.model_name}
        # 異なる優先度で同じモデルが選ばれる場合もあるので、最低1つのモデルが選ばれていることを確認
        assert len(models) >= 1


@pytest.mark.asyncio
async def test_config_reload():
    """設定リロードのテスト"""
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / "reload_test.yaml"
    
    # 初期設定
    initial_config = {
        "llm_models": {
            "test-model": {
                "provider": "test",
                "task": "llm"
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(initial_config, f)
    
    registry = ModelRegistry(str(config_path))
    
    # 初期状態確認
    assert registry.get_model_info("test-model") is not None
    
    # 設定ファイルを更新
    updated_config = {
        "llm_models": {
            "test-model": {
                "provider": "updated",
                "task": "llm",
                "new_field": "added"
            },
            "new-model": {
                "provider": "new",
                "task": "llm"
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(updated_config, f)
    
    # リロード実行
    success = await registry.reload_config()
    assert success is True
    
    # 更新確認
    updated_info = registry.get_model_info("test-model")
    assert updated_info["provider"] == "updated"
    assert updated_info["new_field"] == "added"
    
    new_model_info = registry.get_model_info("new-model")
    assert new_model_info is not None
    assert new_model_info["provider"] == "new"


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])