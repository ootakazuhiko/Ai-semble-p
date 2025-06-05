# Ai-semble v2 本番デプロイメントガイド

## 🎯 概要

このガイドは、Ai-semble v2をPodman環境で本番運用するための包括的な手順を提供します。

## 📋 前提条件チェック

### システム要件

```bash
# OS要件確認
cat /etc/os-release

# 推奨OS:
# - Red Hat Enterprise Linux 8/9
# - CentOS Stream 8/9  
# - Fedora 36+
# - Ubuntu 22.04+
```

### 必須パッケージ確認

```bash
# Podman 4.0+
podman --version

# systemd
systemctl --version

# crun (GPU使用時)
crun --version

# 必要なディスク容量 (最小50GB推奨)
df -h

# メモリ (最小16GB推奨)
free -h

# CPU (最小4コア推奨)
nproc
```

## 🔧 環境セットアップ

### 1. ユーザー設定

```bash
# 専用ユーザー作成
sudo useradd -m -s /bin/bash ai-semble
sudo usermod -aG wheel ai-semble  # RHEL/CentOS
# sudo usermod -aG sudo ai-semble  # Ubuntu

# ユーザー切り替え
sudo su - ai-semble

# Rootless設定
loginctl enable-linger ai-semble

# ユーザー名前空間設定 (管理者権限で実行)
echo "ai-semble:100000:65536" | sudo tee -a /etc/subuid
echo "ai-semble:100000:65536" | sudo tee -a /etc/subgid
```

### 2. セキュリティ設定

```bash
# SELinux設定 (管理者権限)
sudo ./scripts/install-security.sh

# ファイアウォール設定確認
sudo firewall-cmd --list-ports
# 8080-8084/tcp が開放されていることを確認
```

### 3. GPU設定 (オプション)

```bash
# NVIDIA Container Toolkit設定
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# GPU認識確認
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

## 🚀 デプロイメント手順

### Phase 1: 基本セットアップ

```bash
# リポジトリクローン
git clone https://github.com/ootakazuhiko/Ai-semble-p.git
cd Ai-semble-p

# セットアップ実行
./scripts/setup.sh 2>&1 | tee setup.log

# 実行結果確認
tail -20 setup.log
```

### Phase 2: 動作確認

```bash
# Pod起動
./scripts/deploy.sh start

# 状態確認
./scripts/deploy.sh status

# ヘルスチェック
./scripts/deploy.sh health
```

### Phase 3: 統合テスト

```bash
# 基本テスト実行
./scripts/run-tests.sh quick

# 統合テスト実行
./scripts/run-tests.sh integration
```

## 📊 動作確認チェックリスト

### 必須チェック項目

- [ ] **Pod起動確認**
  ```bash
  podman pod ps | grep ai-semble
  # ai-semble   Running   5 containers
  ```

- [ ] **全サービス起動確認**
  ```bash
  podman ps --pod | grep ai-semble
  # 5つのコンテナが全てRunning状態
  ```

- [ ] **ヘルスチェック**
  ```bash
  curl http://localhost:8080/health
  # {"status":"healthy",...}
  ```

- [ ] **各サービス個別確認**
  ```bash
  # Orchestrator
  curl http://localhost:8080/health
  
  # LLM Service
  curl http://localhost:8081/health
  
  # Vision Service
  curl http://localhost:8082/health
  
  # NLP Service
  curl http://localhost:8083/health
  
  # Data Processor
  curl http://localhost:8084/health
  ```

### 機能テスト

- [ ] **LLM推論テスト**
  ```bash
  curl -X POST http://localhost:8080/ai/llm/completion \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Hello","max_tokens":10}'
  ```

- [ ] **画像解析テスト**
  ```bash
  curl -X POST http://localhost:8080/ai/vision/analyze \
    -H "Content-Type: application/json" \
    -d '{"image_base64":"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==","task":"analyze"}'
  ```

- [ ] **NLP処理テスト**
  ```bash
  curl -X POST http://localhost:8080/ai/nlp/process \
    -H "Content-Type: application/json" \
    -d '{"text":"This is great!","task":"sentiment"}'
  ```

- [ ] **データ処理テスト**
  ```bash
  curl -X POST http://localhost:8080/data/process \
    -H "Content-Type: application/json" \
    -d '{"operation":"analyze","data":{"records":[{"id":1,"value":100}]}}'
  ```

### パフォーマンステスト

- [ ] **レスポンス時間計測**
  ```bash
  # 複数回実行してレスポンス時間を確認
  for i in {1..5}; do
    time curl -s http://localhost:8080/health > /dev/null
  done
  ```

- [ ] **同時接続テスト**
  ```bash
  # Apache Bench (ab) でテスト
  ab -n 100 -c 10 http://localhost:8080/health
  ```

- [ ] **リソース使用量確認**
  ```bash
  # CPU・メモリ使用量
  podman stats --no-stream
  
  # ディスク使用量
  podman system df
  ```

## 🔍 トラブルシューティング

### よくある問題と解決方法

#### 1. Pod起動エラー

**症状**: `./scripts/deploy.sh start` でエラー

**確認項目**:
```bash
# systemd status確認
systemctl --user status ai-semble.pod

# ログ確認
journalctl --user -u ai-semble.pod -f

# Quadlet設定確認
ls -la ~/.config/containers/systemd/
```

**解決方法**:
```bash
# systemd設定リロード
systemctl --user daemon-reload

# 手動Pod作成テスト
podman pod create --name test-pod
podman pod rm test-pod
```

#### 2. ネットワーク接続エラー

**症状**: サービス間通信ができない

**確認項目**:
```bash
# ネットワーク状態確認
podman network ls
podman network inspect ai-semble

# ファイアウォール確認
sudo firewall-cmd --list-all
```

**解決方法**:
```bash
# ネットワーク再作成
podman network rm ai-semble
podman network create ai-semble
```

#### 3. GPU認識エラー

**症状**: NVIDIA GPUが認識されない

**確認項目**:
```bash
# GPU状態確認
nvidia-smi

# CDI設定確認
ls -la /etc/cdi/

# crun設定確認
podman info | grep -i crun
```

**解決方法**:
```bash
# CDI再生成
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

# crun設定
sudo update-alternatives --set oci-runtime /usr/bin/crun
```

#### 4. ボリューム権限エラー

**症状**: データボリュームへのアクセスエラー

**確認項目**:
```bash
# ボリューム状態確認
podman volume ls
podman volume inspect ai-semble-data

# SELinuxコンテキスト確認
ls -laZ ~/.local/share/containers/storage/volumes/
```

**解決方法**:
```bash
# SELinuxラベル修正
restorecon -R ~/.local/share/containers/storage/volumes/

# ボリューム再作成
podman volume rm ai-semble-data ai-semble-models
./scripts/setup.sh
```

## 📈 監視・メンテナンス

### 日常監視項目

```bash
# 定期実行推奨 (cron等で自動化)

# サービス状態確認
./scripts/deploy.sh status

# ヘルスチェック
./scripts/deploy.sh health

# リソース使用量確認
podman stats --no-stream

# ログ確認
journalctl --user -u ai-semble.pod --since "1 hour ago"
```

### バックアップ

```bash
# 設定ファイルバックアップ
tar -czf ai-semble-config-$(date +%Y%m%d).tar.gz \
  ~/.config/containers/systemd/ \
  ~/ai-semble-p/

# ボリュームデータバックアップ
podman volume export ai-semble-data > ai-semble-data-$(date +%Y%m%d).tar
```

### 更新手順

```bash
# 新バージョンへの更新
git pull origin main
./scripts/deploy.sh stop
./scripts/setup.sh
./scripts/deploy.sh start
./scripts/deploy.sh health
```

## 🚨 緊急時対応

### サービス停止手順

```bash
# 通常停止
./scripts/deploy.sh stop

# 強制停止
podman pod kill ai-semble
podman pod rm ai-semble
```

### データ復旧手順

```bash
# ボリュームデータ復元
podman volume import ai-semble-data ai-semble-data-20241205.tar

# Pod再起動
./scripts/deploy.sh start
```

### 連絡先

- **技術サポート**: [サポート窓口]
- **緊急連絡先**: [緊急連絡先]
- **ドキュメント**: https://github.com/ootakazuhiko/Ai-semble-p

---

このガイドに従って慎重にデプロイメントを実行してください。問題が発生した場合は、ログを確認して適切な対処を行ってください。