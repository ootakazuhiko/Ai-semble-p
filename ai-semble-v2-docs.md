# Ai-semble v2 開発ドキュメント

## 1. プロジェクト概要

### 1.1 目的
Podmanネイティブな設計により、複数AI開発環境の独立性とセキュリティを確保したオーケストレーション基盤を構築する。

### 1.2 主要変更点
- Docker依存からPodman/systemdネイティブへ
- Rootless実行をデフォルト化
- Pod単位でのサービス管理
- Kubernetes互換性の確保

## 2. アーキテクチャ設計

### 2.1 全体構成
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

### 2.2 ディレクトリ構造
```
ai-semble-v2/
├── containers/
│   ├── orchestrator/
│   │   ├── Containerfile
│   │   └── src/
│   ├── ai-services/
│   │   ├── llm/
│   │   ├── vision/
│   │   └── nlp/
│   └── data-processor/
├── pods/
│   ├── ai-semble.yaml
│   └── ai-semble-dev.yaml
├── quadlets/
│   ├── ai-semble.pod
│   ├── ai-semble.volume
│   └── ai-semble.network
├── security/
│   ├── seccomp/
│   └── selinux/
└── scripts/
    ├── setup.sh
    └── deploy.sh
```

## 3. 実装仕様

### 3.1 Pod定義
```yaml
# pods/ai-semble.yaml
apiVersion: v1
kind: Pod
metadata:
  name: ai-semble
  labels:
    app: ai-semble
spec:
  containers:
  - name: orchestrator
    image: localhost/ai-semble/orchestrator:latest
    ports:
    - containerPort: 8080
    volumeMounts:
    - name: shared-data
      mountPath: /data
    - name: models
      mountPath: /models
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      
  - name: llm-service
    image: localhost/ai-semble/llm:latest
    resources:
      limits:
        memory: "8Gi"
        nvidia.com/gpu: 1
    volumeMounts:
    - name: models
      mountPath: /models
      readOnly: true
      
  - name: data-processor
    image: localhost/ai-semble/processor:latest
    volumeMounts:
    - name: shared-data
      mountPath: /data
      
  volumes:
  - name: shared-data
    persistentVolumeClaim:
      claimName: ai-semble-data
  - name: models
    persistentVolumeClaim:
      claimName: ai-semble-models
```

### 3.2 Quadlet設定
```ini
# quadlets/ai-semble.pod
[Unit]
Description=Ai-semble AI Orchestration Pod
After=network-online.target

[Pod]
PodName=ai-semble
Network=ai-semble.network
Volume=ai-semble-data.volume
Volume=ai-semble-models.volume
PublishPort=8080:8080

[Service]
Type=forking
Environment="PODMAN_SYSTEMD_UNIT=%n"
Restart=on-failure
TimeoutStopSec=70
ExecStartPre=/bin/rm -f %t/%n.ctr-id
ExecStart=/usr/bin/podman pod create \
    --infra-conmon-pidfile %t/%n.pid \
    --pod-id-file %t/%n.pod-id \
    --replace \
    --name ai-semble
ExecStop=/usr/bin/podman pod stop --ignore --pod-id-file %t/%n.pod-id
ExecStopPost=/usr/bin/podman pod rm --ignore -f --pod-id-file %t/%n.pod-id

[Install]
WantedBy=default.target
```

### 3.3 ネットワーク設定
```ini
# quadlets/ai-semble.network
[Unit]
Description=Ai-semble Network

[Network]
Driver=bridge
Internal=false
Subnet=10.88.0.0/24
Gateway=10.88.0.1
Label=app=ai-semble
```

## 4. セキュリティ設計

### 4.1 Rootless実行
```bash
# ユーザー名前空間の設定
loginctl enable-linger $USER
echo "$USER:100000:65536" | sudo tee /etc/subuid
echo "$USER:100000:65536" | sudo tee /etc/subgid
```

### 4.2 SELinuxポリシー
```
# security/selinux/ai_semble.te
policy_module(ai_semble, 1.0.0)

require {
    type container_t;
    type user_home_t;
}

# AIモデルへの読み取り専用アクセス
allow container_t user_home_t:file { read open };
```

### 4.3 Seccompプロファイル
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    {
      "names": ["read", "write", "open", "close", "stat", "fstat"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

## 5. 開発・運用ガイド

### 5.1 初期セットアップ
```bash
#!/bin/bash
# scripts/setup.sh

# Podman設定
systemctl --user enable podman.socket

# ボリューム作成
podman volume create ai-semble-data
podman volume create ai-semble-models

# ネットワーク作成
podman network create ai-semble

# イメージビルド
for dir in containers/*; do
    podman build -t localhost/ai-semble/$(basename $dir):latest $dir
done

# Quadlet設定配置
mkdir -p ~/.config/containers/systemd/
cp quadlets/* ~/.config/containers/systemd/

# systemdリロード
systemctl --user daemon-reload
```

### 5.2 デプロイメント
```bash
# Pod起動
systemctl --user start ai-semble.pod

# ステータス確認
podman pod ps
podman ps --pod

# ログ確認
journalctl --user -u ai-semble.pod
```

### 5.3 開発環境
```yaml
# pods/ai-semble-dev.yaml
# ホットリロード対応の開発用Pod定義
spec:
  containers:
  - name: orchestrator-dev
    image: localhost/ai-semble/orchestrator:dev
    command: ["python", "-m", "flask", "run", "--reload"]
    volumeMounts:
    - name: source-code
      mountPath: /app
    env:
    - name: FLASK_ENV
      value: development
```

## 6. マイグレーション計画

### 6.1 段階的移行
1. **Phase 1**: インフラ層の再実装（2週間）
   - Podman環境構築
   - 基本Pod定義作成
   
2. **Phase 2**: サービス移植（3週間）
   - 既存ロジックのコンテナ化
   - Pod間通信の実装
   
3. **Phase 3**: 本番移行（1週間）
   - 並行稼働テスト
   - 切り替え作業

### 6.2 互換性維持
```yaml
# docker-compose互換用設定
# podman-compose.yaml
version: '3'
services:
  orchestrator:
    image: localhost/ai-semble/orchestrator:latest
    ports:
      - "8080:8080"
```

## 7. 監視・ロギング

### 7.1 Prometheus連携
```yaml
# Pod内にexporter追加
- name: metrics-exporter
  image: prom/node-exporter:latest
  ports:
  - containerPort: 9100
```

### 7.2 構造化ログ
```python
# 共通ログフォーマット
import structlog
logger = structlog.get_logger()
logger.info("ai_operation", 
    service="orchestrator",
    operation="llm_call",
    duration_ms=150)
```

## 8. テスト戦略

### 8.1 ユニットテスト
```bash
# コンテナ内でのテスト実行
podman run --rm \
  -v ./tests:/tests:Z \
  localhost/ai-semble/orchestrator:test \
  pytest /tests
```

### 8.2 統合テスト
```bash
# Pod全体のテスト
podman play kube pods/ai-semble-test.yaml
./scripts/integration-test.sh
```

## 9. パフォーマンスチューニング

### 9.1 リソース制限
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### 9.2 GPU利用
```bash
# NVIDIA Container Toolkit設定
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
podman run --device nvidia.com/gpu=all
```

## 10. トラブルシューティング

### 10.1 よくある問題
- **rootless GPU access**: crun使用を確認
- **ネットワーク接続**: firewalld設定確認
- **ボリューム権限**: `:Z`オプション使用

### 10.2 デバッグコマンド
```bash
# Pod内部調査
podman exec -it ai-semble-orchestrator /bin/bash

# ネットワーク確認
podman network inspect ai-semble

# リソース使用状況
podman stats --no-stream
```