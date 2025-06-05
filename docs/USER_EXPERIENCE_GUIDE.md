# Ai-semble v2 ユーザー体験ガイド

## 🎯 概要

Ai-semble v2は、データサイエンティスト、AI研究者、開発者が様々なAI処理を統合されたプラットフォーム上で実行できる、セキュアなAIオーケストレーション基盤です。

## 👥 対象ユーザー

### プライマリユーザー
- **データサイエンティスト**: データ分析・機械学習パイプライン構築
- **AI研究者**: 複数モデルの比較実験・評価
- **AIアプリ開発者**: AI機能を組み込んだアプリケーション開発

### セカンダリユーザー  
- **システム管理者**: プラットフォーム運用・管理
- **セキュリティ担当者**: セキュリティ監査・コンプライアンス確認

## 🚀 ユーザージャーニー

### シナリオ1: データサイエンティストによる探索的データ分析

**背景**: マーケティングチームから顧客データの分析依頼

#### ステップ1: プラットフォーム起動
```bash
# AI-semble v2を起動
./scripts/deploy.sh start

# 起動確認
curl http://localhost:8080/health
# {"status":"healthy","timestamp":1701234567.89,"service":"orchestrator","version":"2.0.0"}
```

#### ステップ2: データのアップロード・前処理
```bash
# 顧客データファイルをアップロード
curl -X POST http://localhost:8080/data/upload \
  -F "file=@customer_data.csv"

# データの基本分析を実行
curl -X POST http://localhost:8080/data/process \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "analyze",
    "data": {"file_path": "/data/customer_data.csv"},
    "options": {"include_correlation": true}
  }'
```

**レスポンス例**:
```json
{
  "status": "completed",
  "result": {
    "shape": [10000, 15],
    "missing_values": {"age": 45, "income": 12},
    "numeric_summary": {
      "age": {"mean": 34.5, "std": 12.3},
      "income": {"mean": 55000, "std": 15000}
    },
    "correlation_matrix": {...}
  },
  "rows_processed": 10000,
  "processing_time": 2.3
}
```

#### ステップ3: AI分析の実行
```bash
# LLMを使用した顧客セグメント分析
curl -X POST http://localhost:8080/ai/llm/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "以下の顧客データ分析結果から、主要な顧客セグメントを3つ提案してください:\n平均年齢: 34.5歳\n平均収入: 55,000円\n相関: 年齢と収入に強い正の相関",
    "max_tokens": 500,
    "temperature": 0.3
  }'
```

**期待される結果**:
```json
{
  "job_id": "llm-001-abc123",
  "status": "completed", 
  "result": "顧客データ分析に基づく3つの主要セグメント:\n\n1. 若年高収入層（25-30歳、年収60万以上）\n- プレミアム製品への興味が高い\n- デジタルチャネル重視\n\n2. 中堅安定層（31-40歳、年収45-60万）\n- ファミリー向け製品に関心\n- コストパフォーマンス重視\n\n3. シニア富裕層（41歳以上、年収65万以上）\n- 高品質・信頼性重視\n- 対面サービス好み"
}
```

### シナリオ2: AI研究者による画像認識モデル比較実験

**背景**: 医療画像診断の精度向上のための複数モデル評価

#### ステップ1: 複数モデルでの画像解析
```bash
# Vision AIサービスで画像解析実行
curl -X POST http://localhost:8080/ai/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/medical_scan.jpg",
    "task": "medical_analysis",
    "options": {
      "models": ["resnet50", "efficientnet", "vision_transformer"],
      "confidence_threshold": 0.8
    }
  }'
```

#### ステップ2: 結果の比較分析
```bash
# 複数モデルの結果を統計的に比較
curl -X POST http://localhost:8080/data/process \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "aggregate",
    "data": {
      "records": [
        {"model": "resnet50", "accuracy": 0.85, "confidence": 0.92},
        {"model": "efficientnet", "accuracy": 0.88, "confidence": 0.89},
        {"model": "vision_transformer", "accuracy": 0.91, "confidence": 0.94}
      ]
    },
    "options": {
      "group_by": ["model"],
      "agg_funcs": {"accuracy": "mean", "confidence": "mean"}
    }
  }'
```

### シナリオ3: 開発者によるリアルタイムAIアプリケーション開発

**背景**: チャットボットアプリケーションにAI機能を統合

#### ステップ1: アプリケーションからの API呼び出し
```python
import requests
import json

class AiSembleClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def chat_completion(self, user_message, context=""):
        payload = {
            "prompt": f"Context: {context}\nUser: {user_message}\nAssistant:",
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{self.base_url}/ai/llm/completion",
            json=payload
        )
        return response.json()
    
    def analyze_sentiment(self, text):
        # 感情分析をLLMで実行
        payload = {
            "prompt": f"以下のテキストの感情を分析してください（ポジティブ/ネガティブ/ニュートラル）:\n{text}",
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{self.base_url}/ai/llm/completion", 
            json=payload
        )
        return response.json()

# 使用例
client = AiSembleClient()

# ユーザーとの対話
user_input = "今日の天気について教えて"
bot_response = client.chat_completion(user_input)
print(f"Bot: {bot_response['result']}")

# 感情分析
sentiment = client.analyze_sentiment(user_input)
print(f"Sentiment: {sentiment['result']}")
```

## 📊 期待される体験価値

### 1. **統合されたワークフロー**
- 複数のAI処理を一つのプラットフォームで実行
- データ前処理からAI分析、結果処理まで一貫した体験
- APIベースでプログラマブルな操作

### 2. **高いセキュリティ**
- Rootless実行による権限分離
- SELinux/Seccompによる多層防御
- 監査ログによる操作追跡

### 3. **スケーラブルな性能**
- GPU対応による高速AI処理
- Pod型アーキテクチャによる水平スケーリング
- リソース制限による安定動作

### 4. **開発者フレンドリー**
- RESTful API設計
- 構造化ログによるデバッグ支援
- Prometheus監視による運用性

## 🎭 ユーザーペルソナ

### ペルソナ1: 田中さん（データサイエンティスト）
- **背景**: 金融機関で顧客行動分析担当、Python/R経験豊富
- **課題**: 複数ツールの連携が複雑、セキュリティ要件が厳しい
- **期待**: 統合環境でのスムーズな分析ワークフロー

**典型的な1日の使用パターン**:
```
09:00 - プラットフォーム起動、データアップロード
10:00 - 基本統計分析実行
11:00 - LLMによる仮説生成
14:00 - 機械学習モデル訓練
16:00 - 結果レポート生成
```

### ペルソナ2: 佐藤さん（AI研究者）
- **背景**: 大学研究室でコンピュータビジョン研究、論文多数
- **課題**: 実験環境の再現性、複数モデルの比較が煩雑
- **期待**: 厳密な実験管理と結果の再現性

**典型的な研究フロー**:
```
準備 - 実験条件設定、データセット準備
実行 - 複数モデルでの並列実験
分析 - 統計的有意性検定、可視化
記録 - 実験ログ保存、論文用データ出力
```

### ペルソナ3: 山田さん（AIアプリ開発者）
- **背景**: スタートアップでWebアプリ開発、AI機能組込み経験少
- **課題**: AI実装の複雑さ、性能・コストの最適化
- **期待**: 簡単なAPI呼び出しで高品質なAI機能

**開発サイクル**:
```
設計 - AI機能要件定義
実装 - API統合、エラーハンドリング
テスト - 性能・精度検証
デプロイ - 本番環境での監視
```

## 🎬 デモシナリオ

### 15分デモ: 「顧客レビュー分析からマーケティング施策提案まで」

1. **データ準備** (2分)
   - 顧客レビューCSVをアップロード
   - 基本統計表示

2. **感情分析** (3分)
   - レビューテキストの感情分析実行
   - ポジティブ/ネガティブ分布表示

3. **キーワード抽出** (3分)
   - LLMによる重要トピック抽出
   - 問題点・改善点の自動識別

4. **施策提案** (5分)
   - 分析結果をもとにしたAI提案
   - 具体的なマーケティング戦略生成

5. **レポート出力** (2分)
   - 結果の構造化データ出力
   - 可視化用データ準備

**期待される成果物**:
- 定量的分析結果（満足度スコア、感情分布）
- 定性的インサイト（主要不満点、改善要望）
- 実行可能な施策提案（優先度付き改善計画）

## 🔄 継続的な改善サイクル

1. **ユーザーフィードバック収集**
   - API使用パターン分析
   - エラーログ分析
   - ユーザーアンケート

2. **機能拡張**
   - 新しいAIモデル追加
   - カスタムワークフロー機能
   - 自動化スクリプト提供

3. **性能最適化**
   - レスポンス時間改善
   - 同時処理数向上
   - リソース効率化

これにより、Ai-semble v2は単なるツールではなく、ユーザーのAI活用を加速するプラットフォームとしての価値を提供します。