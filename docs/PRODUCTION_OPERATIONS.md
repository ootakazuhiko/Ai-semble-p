# Ai-semble v2 本番運用ガイド

## 🎯 概要

このドキュメントは、Ai-semble v2の本番環境での運用に必要な監視・ログ・バックアップ機能について説明します。

## 🔧 監視システム

### システム監視機能

#### 自動監視項目
- **システムリソース**: CPU、メモリ、ディスク使用率
- **サービスヘルス**: 各マイクロサービスの応答性
- **ネットワーク**: 接続数、レスポンス時間
- **エラー率**: HTTP エラー、アプリケーションエラー
- **AIモデル**: 推論時間、失敗率

#### Prometheusメトリクス
```
# システムメトリクス
aisemble_system_cpu_usage_percent
aisemble_system_memory_usage_percent
aisemble_system_disk_usage_percent

# サービスメトリクス
aisemble_requests_total
aisemble_request_duration_seconds
aisemble_active_connections

# AIモデルメトリクス
aisemble_model_inference_total
aisemble_model_inference_duration_seconds

# エラーメトリクス
aisemble_errors_total
```

### アラート設定

#### 重要度別アラート
1. **Critical**: システム停止、データ損失リスク
2. **Warning**: 性能劣化、リソース不足の兆候
3. **Info**: 一般的な状態変化

#### 主要アラートルール
- CPU使用率 > 80% (5分間)
- メモリ使用率 > 85% (5分間)
- ディスク使用率 > 80% (10分間)
- サービス応答なし (1分間)
- エラー率 > 5% (3分間)

## 📊 ログ管理

### 構造化ログ

#### ログ形式
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "service": "orchestrator",
  "message": "Request processed successfully",
  "context": {
    "request_id": "req_123",
    "user_id": "user_456",
    "processing_time": 0.125
  },
  "trace_id": "trace_789"
}
```

#### ログレベル
- **DEBUG**: 開発・デバッグ情報
- **INFO**: 一般的な動作情報
- **WARNING**: 警告（動作継続可能）
- **ERROR**: エラー（機能に影響）
- **CRITICAL**: 重大エラー（システム停止レベル）

### ログ保存・管理

#### ローテーション設定
- **一般ログ**: 30日保持、日次ローテーション
- **エラーログ**: 30日保持、日次ローテーション
- **監査ログ**: 90日保持、改ざん防止

#### 検索・分析機能
- 時間範囲フィルタ
- ログレベルフィルタ
- サービス別フィルタ
- 全文検索
- トレースID追跡

## 💾 バックアップシステム

### 自動バックアップ

#### バックアップ対象
1. **システム設定**: 設定ファイル、Pod定義
2. **ログデータ**: アプリケーション・システムログ
3. **AIモデル**: 学習済みモデル、カスタムモデル
4. **データ**: ユーザーデータ、セッション情報

#### スケジュール
```yaml
# システム設定: 毎日2時
system_config:
  schedule: "0 2 * * *"
  retention: 30日

# ログ: 毎日3時  
logs:
  schedule: "0 3 * * *"
  retention: 7日

# モデル: 毎週日曜1時
models:
  schedule: "0 1 * * 0"
  retention: 14日

# データ: 毎日4時
data:
  schedule: "0 4 * * *"
  retention: 14日
```

### 復元機能

#### 復元手順
1. バックアップファイル選択
2. 復元先指定
3. 整合性チェック
4. 段階的復元実行
5. 動作確認

## 🖥️ 運用ダッシュボード

### リアルタイム監視

#### ダッシュボード起動
```bash
# インタラクティブダッシュボード
python3 scripts/operations_dashboard.py --mode dashboard

# シンプル状況確認
python3 scripts/operations_dashboard.py --mode status
```

#### 表示項目
- **システム状況**: CPU、メモリ、ディスク
- **サービス詳細**: 応答時間、エラー数
- **ログ統計**: エラー率、ログ分布
- **バックアップ状況**: スケジュール、成功率
- **最新アラート**: 重要度別表示

## 🔍 API エンドポイント

### 監視API
```
GET /ops/status                 - システム全体状況
GET /ops/health/comprehensive   - 包括的ヘルスチェック
POST /ops/monitoring/start      - 監視開始
POST /ops/monitoring/stop       - 監視停止
```

### ログAPI
```
POST /ops/logs/search          - ログ検索
GET /ops/logs/stats           - ログ統計
POST /ops/logs/export         - ログエクスポート
POST /ops/logs/audit          - 監査ログ作成
```

### バックアップAPI
```
GET /ops/backups/status       - バックアップ状況
POST /ops/backups/jobs        - ジョブ作成
POST /ops/backups/manual      - 手動バックアップ
POST /ops/backups/restore     - 復元実行
```

## 🚨 アラート通知

### 通知チャネル設定

#### Slack通知（例）
```python
# services/monitoring.py 内の _send_alert_notification を拡張
async def _send_alert_notification(self, alert_data: Dict[str, Any]):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        message = {
            "text": f"🚨 Alert: {alert_data['rule_name']}",
            "color": "danger" if alert_data['severity'] == "critical" else "warning"
        }
        await self._send_slack_message(webhook_url, message)
```

### メール通知設定
```python
# SMTP設定例
smtp_config = {
    "server": "smtp.example.com",
    "port": 587,
    "username": "alerts@example.com",
    "password": os.getenv("SMTP_PASSWORD"),
    "recipients": ["admin@example.com"]
}
```

## 📈 パフォーマンス監視

### 主要指標

#### システムパフォーマンス
- **スループット**: リクエスト/秒
- **レスポンス時間**: P50, P95, P99
- **エラー率**: 4xx, 5xx エラー
- **可用性**: アップタイム割合

#### AIモデルパフォーマンス
- **推論時間**: モデル別平均時間
- **成功率**: 推論成功/失敗比
- **キュー時間**: バッチ処理待機時間
- **スループット**: 推論/秒

### 最適化指針

#### 自動スケーリング
- CPU使用率 > 70% で Pod 追加
- メモリ使用率 > 80% で Pod 追加
- リクエスト数に基づく予測スケーリング

#### キャッシュ最適化
- 頻繁なリクエストのキャッシュ
- モデル結果の一時保存
- 設定データのメモリキャッシュ

## 🔐 セキュリティ監視

### 監査ログ

#### 記録対象
- ユーザー認証・認可
- 管理操作（設定変更、モデル追加）
- データアクセス
- システム設定変更

#### 不正検知
- 異常なアクセスパターン
- 権限昇格の試行
- 大量データアクセス
- システムファイル変更

## 🛠️ トラブルシューティング

### 一般的な問題

#### 高CPU使用率
```bash
# 原因調査
kubectl top pods
kubectl logs <pod-name>

# 対処
kubectl scale deployment <service> --replicas=3
```

#### メモリ不足
```bash
# メモリ使用量確認
kubectl describe node <node-name>

# Pod再起動
kubectl rollout restart deployment <service>
```

#### ディスク容量不足
```bash
# 古いログ削除
curl -X POST http://localhost:8080/ops/logs/cleanup

# 古いバックアップ削除
find /var/backups -name "*.tar.gz" -mtime +30 -delete
```

### サービス復旧手順

#### 1. 問題特定
- ログ確認
- メトリクス分析
- 外部依存関係チェック

#### 2. 応急対応
- 影響サービス特定
- 負荷分散調整
- 緊急スケールアウト

#### 3. 根本対応
- 設定修正
- コード修正
- インフラ調整

#### 4. 事後対応
- 監査ログ記録
- 改善策策定
- 監視強化

## 📝 運用チェックリスト

### 日次チェック
- [ ] システム全体ヘルス確認
- [ ] エラー率・レスポンス時間確認
- [ ] ディスク使用量確認
- [ ] バックアップ成功確認

### 週次チェック
- [ ] ログローテーション確認
- [ ] セキュリティアラート確認
- [ ] パフォーマンストレンド分析
- [ ] 容量計画見直し

### 月次チェック
- [ ] 監視しきい値見直し
- [ ] バックアップ復元テスト
- [ ] セキュリティパッチ適用
- [ ] 災害復旧計画確認

このガイドに従って運用することで、Ai-semble v2の安定稼働と早期問題検知が可能になります。