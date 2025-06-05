# Ai-semble v2

Podmanネイティブな設計による、複数AI開発環境の独立性とセキュリティを確保したオーケストレーション基盤

## 概要

Ai-semble v2は、DockerからPodman/systemdネイティブへ移行し、Rootless実行をデフォルトとしたAIオーケストレーションプラットフォームです。Pod単位でのサービス管理により、セキュリティと分離性を向上させています。

### 主要機能

- **Podmanネイティブ設計**: Docker依存を排除し、Podman/systemdで統合管理
- **Rootless実行**: セキュリティ強化のためのrootless環境
- **Pod型アーキテクチャ**: 複数コンテナの協調動作
- **GPU対応**: NVIDIA Container Toolkit統合
- **セキュリティ強化**: SELinux、Seccomp、AppArmor対応
- **監視・ロギング**: Prometheus、構造化ログ対応

## アーキテクチャ

```
┌─────────────────────────────────────────────┐
│  Ai-semble Pod                              │
├─────────────┬─────────────┬─────────────────┤
│ Orchestrator│ AI Services │ Data Processor  │
│  Container  │  Container  │   Container     │
├─────────────┴─────────────┴─────────────────┤
│         Shared Volume (Named Volumes)        │
├─────────────────────────────────────────────┤
│    Podman (Rootless) + systemd              │
└─────────────────────────────────────────────┘
```

### コンテナ構成

- **Orchestrator**: メインAPI・ワークフロー管理 (ポート: 8080)
- **LLM Service**: 大規模言語モデル推論 (ポート: 8081)
- **Vision Service**: 画像解析・コンピュータビジョン (ポート: 8082)
- **NLP Service**: 自然言語処理・テキスト分析 (ポート: 8083)
- **Data Processor**: データ処理・ETL (ポート: 8084)

## クイックスタート

### 前提条件

- Podman 4.0+
- systemd (ユーザーサービス有効)
- Linux環境 (RHEL/CentOS/Fedora/Ubuntu推奨)
- (オプション) NVIDIA GPU + NVIDIA Container Toolkit

### セットアップ

1. **セキュリティ設定インストール (管理者権限)**
   ```bash
   sudo ./scripts/install-security.sh
   ```

2. **基本セットアップ (一般ユーザー)**
   ```bash
   ./scripts/setup.sh
   ```

3. **Pod開始**
   ```bash
   ./scripts/deploy.sh start
   ```

4. **動作確認**
   ```bash
   curl http://localhost:8080/health
   ```

## 開発環境

### 開発Podの起動

```bash
./scripts/deploy.sh start --dev
```

### ログ確認

```bash
./scripts/deploy.sh logs --follow
```

### ヘルスチェック

```bash
./scripts/deploy.sh health
```

## API仕様

### Orchestrator API

- `GET /health` - ヘルスチェック
- `POST /ai/llm/completion` - LLM推論実行
- `POST /ai/vision/analyze` - 画像解析実行
- `POST /ai/nlp/process` - NLP処理実行
- `POST /data/process` - データ処理実行
- `GET /jobs/{id}` - ジョブ状態確認
- `GET /metrics` - Prometheusメトリクス

### 使用例

```bash
# LLM推論
curl -X POST http://localhost:8080/ai/llm/completion \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Hello, how are you?",
    "max_tokens": 100,
    "temperature": 0.7
  }'

# 画像解析
curl -X POST http://localhost:8080/ai/vision/analyze \\
  -H "Content-Type: application/json" \\
  -d '{
    "image_url": "https://example.com/image.jpg",
    "task": "analyze"
  }'

# NLP処理（感情分析）
curl -X POST http://localhost:8080/ai/nlp/process \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "This is a great product!",
    "task": "sentiment"
  }'

# データ処理
curl -X POST http://localhost:8080/data/process \\
  -H "Content-Type: application/json" \\
  -d '{
    "operation": "analyze",
    "data": {"records": [{"id": 1, "value": 100}]}
  }'
```

## ディレクトリ構造

```
ai-semble-v2/
├── containers/          # コンテナ定義
│   ├── orchestrator/    # メインサービス
│   ├── ai-services/     # AIサービス群
│   └── data-processor/  # データ処理
├── pods/               # Pod定義ファイル
├── quadlets/           # systemd Quadlet設定
├── security/           # セキュリティポリシー
├── scripts/            # 運用スクリプト
├── tests/              # テストスイート
├── docs/               # ドキュメント
└── configs/            # 設定ファイル
```

## 運用コマンド

### Pod管理

```bash
# 開始
./scripts/deploy.sh start

# 停止  
./scripts/deploy.sh stop

# 再起動
./scripts/deploy.sh restart

# 状態確認
./scripts/deploy.sh status

# イメージ更新
./scripts/deploy.sh update
```

### 直接操作

```bash
# Pod状態確認
podman pod ps

# コンテナ状態確認
podman ps --pod

# ログ確認
journalctl --user -u ai-semble.pod -f

# ネットワーク確認
podman network ls

# ボリューム確認
podman volume ls
```

## セキュリティ

### 実装済みセキュリティ機能

- **Rootless実行**: 非root権限での動作
- **SELinux**: カスタムポリシーによるアクセス制御
- **Seccomp**: システムコール制限
- **Read-only filesystem**: 不変なルートファイルシステム
- **Network isolation**: Pod内部ネットワーク分離
- **リソース制限**: CPU・メモリ使用量制限

### セキュリティ設定確認

```bash
# SELinuxポリシー確認
semodule -l | grep ai_semble

# Seccompプロファイル確認  
ls -la /etc/containers/seccomp/

# ファイアウォール確認
firewall-cmd --list-ports
```

## 監視・ロギング

### メトリクス収集

- Prometheusメトリクス: `http://localhost:8080/metrics`
- 構造化ログ: JSON形式でjournald出力

### ログ分析

```bash
# エラーログ検索
journalctl --user -u ai-semble.pod | grep ERROR

# 特定サービスのログ
podman logs ai-semble-orchestrator

# リアルタイムログ
./scripts/deploy.sh logs --follow
```

## トラブルシューティング

### よくある問題

1. **rootless GPU access**
   ```bash
   # NVIDIA Container Toolkit設定確認
   sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
   ```

2. **ネットワーク接続エラー**
   ```bash
   # ファイアウォール確認
   sudo firewall-cmd --list-ports
   ```

3. **ボリューム権限エラー**
   ```bash
   # SELinuxコンテキスト確認
   ls -laZ /var/lib/containers/storage/volumes/
   ```

### デバッグ

```bash
# コンテナ内部確認
podman exec -it ai-semble-orchestrator /bin/bash

# ネットワーク詳細
podman network inspect ai-semble

# リソース使用状況
podman stats --no-stream
```

## 開発貢献

### テスト実行

```bash
# 全テスト実行
./scripts/run-tests.sh all

# ユニットテストのみ
./scripts/run-tests.sh unit

# 統合テストのみ（サービス起動後）
./scripts/deploy.sh start
./scripts/run-tests.sh integration

# コード品質チェック
./scripts/run-tests.sh lint

# 簡易テスト
./scripts/run-tests.sh quick

# カバレッジ付きテスト
./scripts/run-tests.sh unit --coverage
```

### イメージビルド

```bash
# 個別ビルド
podman build -t localhost/ai-semble/orchestrator:latest containers/orchestrator/

# 全体ビルド
./scripts/setup.sh
```

## ライセンス

[ライセンス情報をここに記載]

## サポート

- Issue報告: [GitHub Issues]
- ドキュメント: `docs/` ディレクトリ
- 技術仕様: `DEVELOPMENT_PLAN.md`
- 開発ガイド: `CLAUDE.md`