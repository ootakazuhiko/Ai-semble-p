#!/usr/bin/env python3
"""
高度なAIモデル統合機能のデモンストレーション
Ai-semble v2の自動モデル選択と動的モデル管理の実演
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
import argparse
from datetime import datetime

class AdvancedAIDemoClient:
    """高度なAI統合機能のデモクライアント"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.close()
    
    async def demo_auto_model_selection(self):
        """自動モデル選択のデモンストレーション"""
        print("🤖 自動モデル選択デモンストレーション")
        print("=" * 50)
        
        # 様々なタスクタイプでの自動選択をテスト
        test_cases = [
            {
                "name": "コード生成タスク",
                "prompt": "def fibonacci(n): # Complete this Python function to calculate fibonacci numbers",
                "priority": "quality"
            },
            {
                "name": "日本語創作タスク", 
                "prompt": "桜が咲く春の日に、小さな村で起こった心温まる物語を書いてください。",
                "priority": "balanced"
            },
            {
                "name": "医療相談タスク",
                "prompt": "What are the common symptoms of diabetes and how can it be managed?",
                "priority": "quality"
            },
            {
                "name": "数学問題タスク",
                "prompt": "Solve this equation: 2x + 5 = 15. Show your work step by step.",
                "priority": "balanced"
            },
            {
                "name": "法律相談タスク",
                "prompt": "What are the key elements of a valid contract under common law?",
                "priority": "quality"
            },
            {
                "name": "コスト重視タスク",
                "prompt": "Write a brief summary of renewable energy benefits.",
                "priority": "cost"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 テストケース {i}: {test_case['name']}")
            print(f"プロンプト: {test_case['prompt'][:50]}...")
            print(f"優先度: {test_case['priority']}")
            
            # モデル選択API呼び出し
            selection_result = await self._call_model_selection(
                test_case['prompt'],
                priority=test_case['priority']
            )
            
            if selection_result:
                print(f"✅ 選択されたモデル: {selection_result['selected_model']}")
                print(f"   信頼度: {selection_result['confidence']:.2f}")
                print(f"   理由: {selection_result['reason']}")
                if selection_result.get('fallback_models'):
                    print(f"   フォールバック: {', '.join(selection_result['fallback_models'])}")
            else:
                print("❌ モデル選択に失敗")
            
            await asyncio.sleep(0.5)  # レート制限を考慮
    
    async def demo_dynamic_model_management(self):
        """動的モデル管理のデモンストレーション"""
        print("\n🔧 動的モデル管理デモンストレーション")
        print("=" * 50)
        
        # 現在のモデル一覧を取得
        print("\n📊 現在登録されているモデル:")
        models = await self._get_models()
        if models:
            for category, category_models in models.get('models', {}).items():
                if isinstance(category_models, dict):
                    print(f"  {category}: {len(category_models)} models")
                    for model_name in list(category_models.keys())[:3]:  # 最初の3つだけ表示
                        print(f"    - {model_name}")
                    if len(category_models) > 3:
                        print(f"    ... and {len(category_models) - 3} more")
        
        # カスタムモデルを登録
        print("\n➕ カスタムモデルの登録:")
        custom_model = {
            "category": "llm_models",
            "model_name": "demo-custom-model",
            "model_info": {
                "provider": "demo",
                "task": "llm",
                "capabilities": ["demo_task", "test_generation"],
                "quality_score": 0.85,
                "speed_score": 0.90,
                "cost_per_token": 0.001,
                "local": True
            }
        }
        
        register_result = await self._register_model(custom_model)
        if register_result:
            print(f"✅ モデル '{custom_model['model_name']}' を正常に登録")
        else:
            print("❌ モデル登録に失敗")
        
        # 登録したモデルの情報を取得
        print(f"\n📖 登録したモデルの詳細情報:")
        model_info = await self._get_model_info(custom_model['model_name'])
        if model_info:
            print(json.dumps(model_info, indent=2, ensure_ascii=False))
        
        # モデル統計を表示
        print(f"\n📈 モデル統計:")
        stats = await self._get_model_stats()
        if stats:
            print(f"  総モデル数: {stats.get('total_models', 0)}")
            print(f"  カテゴリ別:")
            for category, count in stats.get('categories', {}).items():
                print(f"    {category}: {count}")
            print(f"  プロバイダー別:")
            for provider, count in stats.get('providers', {}).items():
                print(f"    {provider}: {count}")
        
        # 登録したモデルを削除（クリーンアップ）
        print(f"\n🗑️  テストモデルのクリーンアップ:")
        delete_result = await self._delete_model(custom_model['model_name'])
        if delete_result:
            print(f"✅ モデル '{custom_model['model_name']}' を削除")
        else:
            print("❌ モデル削除に失敗")
    
    async def demo_smart_llm_completion(self):
        """スマートLLM補完のデモンストレーション"""
        print("\n🧠 スマートLLM補完デモンストレーション")
        print("=" * 50)
        
        # 異なる優先度での同じタスクのテスト
        test_prompt = "Explain the concept of machine learning in simple terms."
        priorities = ["quality", "cost", "balanced"]
        
        for priority in priorities:
            print(f"\n🎯 優先度: {priority}")
            
            request_data = {
                "prompt": test_prompt,
                "model": "auto",  # 自動選択
                "max_tokens": 150,
                "temperature": 0.7,
                "priority": priority,
                "auto_select": True
            }
            
            start_time = time.time()
            result = await self._call_llm_completion(request_data)
            end_time = time.time()
            
            if result:
                print(f"✅ 処理完了:")
                print(f"   使用モデル: {result.get('model_used', 'N/A')}")
                print(f"   選択理由: {result.get('selection_reason', 'N/A')}")
                print(f"   処理時間: {result.get('processing_time', 0):.2f}秒")
                print(f"   レスポンス時間: {end_time - start_time:.2f}秒")
                print(f"   結果プレビュー: {result.get('result', '')[:100]}...")
            else:
                print("❌ LLM補完に失敗")
            
            await asyncio.sleep(1)  # 次のリクエストまで待機
    
    async def demo_capability_based_search(self):
        """能力ベース検索のデモンストレーション"""
        print("\n🔍 能力ベース検索デモンストレーション")
        print("=" * 50)
        
        capabilities_to_test = [
            "text_generation",
            "code_generation", 
            "image_segmentation",
            "sentiment_analysis",
            "translation"
        ]
        
        for capability in capabilities_to_test:
            print(f"\n🎯 能力: {capability}")
            
            models = await self._get_models_by_capability(capability)
            if models and models.get('models'):
                print(f"✅ {len(models['models'])} models found:")
                for model in models['models'][:5]:  # 最初の5つまで表示
                    print(f"   - {model}")
                if len(models['models']) > 5:
                    print(f"   ... and {len(models['models']) - 5} more")
            else:
                print(f"❌ 能力 '{capability}' を持つモデルが見つかりません")
    
    async def demo_comprehensive_workflow(self):
        """包括的ワークフローのデモンストレーション"""
        print("\n🚀 包括的ワークフローデモンストレーション")
        print("=" * 50)
        
        # 1. ヘルスチェック
        print("\n1️⃣ システムヘルスチェック")
        health_result = await self._check_health()
        if health_result:
            print("✅ システムは正常に動作中")
        else:
            print("❌ システムに問題があります")
            return
        
        # 2. モデル統計の表示
        print("\n2️⃣ システムの現在状態")
        stats = await self._get_model_stats()
        if stats:
            print(f"登録済みモデル: {stats.get('total_models', 0)}")
        
        # 3. マルチタスクでの自動選択テスト
        print("\n3️⃣ マルチタスク自動選択テスト")
        tasks = [
            "Write a Python function to reverse a string",
            "日本語で俳句を作ってください", 
            "Explain quantum computing basics"
        ]
        
        for i, task in enumerate(tasks, 1):
            print(f"\nタスク {i}: {task}")
            selection = await self._call_model_selection(task)
            if selection:
                print(f"  → 選択: {selection['selected_model']} (信頼度: {selection['confidence']:.2f})")
        
        # 4. パフォーマンス測定
        print("\n4️⃣ パフォーマンス測定")
        request_data = {
            "prompt": "Quick test prompt for performance measurement",
            "model": "auto",
            "max_tokens": 50
        }
        
        times = []
        for i in range(3):
            start = time.time()
            result = await self._call_llm_completion(request_data)
            end = time.time()
            if result:
                times.append(end - start)
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"  平均レスポンス時間: {avg_time:.2f}秒")
            print(f"  最小時間: {min(times):.2f}秒")
            print(f"  最大時間: {max(times):.2f}秒")
    
    # ヘルパーメソッド
    async def _call_model_selection(self, prompt: str, priority: str = "balanced") -> Dict[str, Any]:
        """モデル選択APIを呼び出し"""
        try:
            async with self.session.post(
                f"{self.base_url}/models/select",
                json={
                    "prompt": prompt,
                    "task_type": "llm",
                    "priority": priority,
                    "max_tokens": 100
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Model selection failed: {response.status}")
                    return None
        except Exception as e:
            print(f"Error calling model selection: {e}")
            return None
    
    async def _get_models(self) -> Dict[str, Any]:
        """モデル一覧を取得"""
        try:
            async with self.session.get(f"{self.base_url}/models/") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting models: {e}")
            return None
    
    async def _register_model(self, model_data: Dict[str, Any]) -> bool:
        """モデルを登録"""
        try:
            async with self.session.post(
                f"{self.base_url}/models/register",
                json=model_data
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"Error registering model: {e}")
            return False
    
    async def _get_model_info(self, model_name: str) -> Dict[str, Any]:
        """モデル情報を取得"""
        try:
            async with self.session.get(f"{self.base_url}/models/{model_name}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting model info: {e}")
            return None
    
    async def _get_model_stats(self) -> Dict[str, Any]:
        """モデル統計を取得"""
        try:
            async with self.session.get(f"{self.base_url}/models/stats") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting model stats: {e}")
            return None
    
    async def _delete_model(self, model_name: str) -> bool:
        """モデルを削除"""
        try:
            async with self.session.delete(f"{self.base_url}/models/{model_name}") as response:
                return response.status == 200
        except Exception as e:
            print(f"Error deleting model: {e}")
            return False
    
    async def _call_llm_completion(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM補完APIを呼び出し"""
        try:
            async with self.session.post(
                f"{self.base_url}/ai/llm/completion",
                json=request_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"LLM completion failed: {response.status}")
                    return None
        except Exception as e:
            print(f"Error calling LLM completion: {e}")
            return None
    
    async def _get_models_by_capability(self, capability: str) -> Dict[str, Any]:
        """能力別モデル一覧を取得"""
        try:
            async with self.session.get(
                f"{self.base_url}/models/capabilities/{capability}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting models by capability: {e}")
            return None
    
    async def _check_health(self) -> bool:
        """ヘルスチェック"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception as e:
            print(f"Error checking health: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Ai-semble v2 Advanced AI Integration Demo")
    parser.add_argument("--url", default="http://localhost:8080", 
                       help="Base URL of Ai-semble v2 orchestrator")
    parser.add_argument("--demo", choices=["auto", "management", "completion", "search", "all"], 
                       default="all", help="Demo type to run")
    
    args = parser.parse_args()
    
    print("🎭 Ai-semble v2 高度なAI統合機能デモンストレーション")
    print("=" * 60)
    print(f"接続先: {args.url}")
    print(f"開始時刻: {datetime.now().isoformat()}")
    print()
    
    async with AdvancedAIDemoClient(args.url) as demo:
        try:
            if args.demo in ["auto", "all"]:
                await demo.demo_auto_model_selection()
            
            if args.demo in ["management", "all"]:
                await demo.demo_dynamic_model_management()
            
            if args.demo in ["completion", "all"]:
                await demo.demo_smart_llm_completion()
            
            if args.demo in ["search", "all"]:
                await demo.demo_capability_based_search()
            
            if args.demo == "all":
                await demo.demo_comprehensive_workflow()
            
            print("\n✅ デモンストレーション完了!")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n⚠️  デモンストレーションが中断されました")
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())