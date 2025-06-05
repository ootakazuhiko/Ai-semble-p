#!/bin/bash
# Ai-semble v2 セットアップスクリプト

set -euo pipefail

# 設定
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-setup.log"

# ログ関数
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE" >&2
}

log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

# 前提条件チェック
check_prerequisites() {
    log_info "前提条件をチェック中..."
    
    # Podman存在確認
    if ! command -v podman &> /dev/null; then
        log_error "Podmanがインストールされていません"
        exit 1
    fi
    
    # systemdユーザーサービス確認
    if ! systemctl --user status &> /dev/null; then
        log_error "systemdユーザーサービスが利用できません"
        exit 1
    fi
    
    # Rootless実行確認
    if [[ "$(id -u)" == "0" ]]; then
        log_error "このスクリプトをrootで実行しないでください"
        exit 1
    fi
    
    log_info "前提条件チェック完了"
}

# Podman設定
setup_podman() {
    log_info "Podman設定を開始..."
    
    # Podmanソケット有効化
    systemctl --user enable podman.socket
    systemctl --user start podman.socket
    
    # ユーザー名前空間設定確認
    if ! grep -q "^$(whoami):" /etc/subuid; then
        log_warn "ユーザー名前空間が設定されていません"
        log_warn "以下のコマンドを管理者権限で実行してください:"
        log_warn "echo '$(whoami):100000:65536' | sudo tee -a /etc/subuid"
        log_warn "echo '$(whoami):100000:65536' | sudo tee -a /etc/subgid"
    fi
    
    # レジストリ設定
    local registries_conf="$HOME/.config/containers/registries.conf"
    mkdir -p "$(dirname "$registries_conf")"
    
    if [[ ! -f "$registries_conf" ]]; then
        cat > "$registries_conf" << 'EOF'
[registries.search]
registries = ['docker.io', 'quay.io', 'registry.fedoraproject.org']

[registries.insecure]
registries = ['localhost']

[registries.block]
registries = []
EOF
        log_info "レジストリ設定を作成しました: $registries_conf"
    fi
    
    log_info "Podman設定完了"
}

# ネットワーク作成
create_network() {
    log_info "ネットワーク作成中..."
    
    if podman network exists ai-semble 2>/dev/null; then
        log_warn "ネットワーク 'ai-semble' は既に存在します"
        return 0
    fi
    
    podman network create \
        --driver bridge \
        --subnet 10.88.0.0/24 \
        --gateway 10.88.0.1 \
        --label app=ai-semble \
        --label version=v2.0.0 \
        ai-semble
    
    log_info "ネットワーク 'ai-semble' を作成しました"
}

# ボリューム作成
create_volumes() {
    log_info "ボリューム作成中..."
    
    # データボリューム
    if ! podman volume exists ai-semble-data 2>/dev/null; then
        podman volume create \
            --driver local \
            --label app=ai-semble \
            --label type=data \
            --label version=v2.0.0 \
            ai-semble-data
        log_info "データボリューム 'ai-semble-data' を作成しました"
    else
        log_warn "データボリューム 'ai-semble-data' は既に存在します"
    fi
    
    # モデルボリューム
    if ! podman volume exists ai-semble-models 2>/dev/null; then
        podman volume create \
            --driver local \
            --label app=ai-semble \
            --label type=models \
            --label version=v2.0.0 \
            ai-semble-models
        log_info "モデルボリューム 'ai-semble-models' を作成しました"
    else
        log_warn "モデルボリューム 'ai-semble-models' は既に存在します"
    fi
}

# コンテナイメージビルド
build_images() {
    log_info "コンテナイメージをビルド中..."
    
    local containers_dir="$PROJECT_ROOT/containers"
    
    # Orchestrator
    log_info "Orchestratorイメージをビルド中..."
    podman build \
        -t localhost/ai-semble/orchestrator:latest \
        -t localhost/ai-semble/orchestrator:dev \
        "$containers_dir/orchestrator"
    
    # LLM Service
    log_info "LLM Serviceイメージをビルド中..."
    podman build \
        -t localhost/ai-semble/llm:latest \
        -t localhost/ai-semble/llm:dev \
        "$containers_dir/ai-services/llm"
    
    # Vision Service
    log_info "Vision Serviceイメージをビルド中..."
    podman build \
        -t localhost/ai-semble/vision:latest \
        -t localhost/ai-semble/vision:dev \
        "$containers_dir/ai-services/vision"
    
    # NLP Service
    log_info "NLP Serviceイメージをビルド中..."
    podman build \
        -t localhost/ai-semble/nlp:latest \
        -t localhost/ai-semble/nlp:dev \
        "$containers_dir/ai-services/nlp"
    
    # Data Processor
    log_info "Data Processorイメージをビルド中..."
    podman build \
        -t localhost/ai-semble/processor:latest \
        -t localhost/ai-semble/processor:dev \
        "$containers_dir/data-processor"
    
    log_info "全てのイメージビルドが完了しました"
}

# Quadlet設定配置
install_quadlets() {
    log_info "Quadlet設定を配置中..."
    
    local systemd_dir="$HOME/.config/containers/systemd"
    mkdir -p "$systemd_dir"
    
    # Quadletファイルをコピー
    cp "$PROJECT_ROOT"/quadlets/*.{pod,network,volume} "$systemd_dir/"
    
    # systemdリロード
    systemctl --user daemon-reload
    
    log_info "Quadlet設定を配置し、systemdをリロードしました"
}

# GPU設定確認
check_gpu_setup() {
    log_info "GPU設定を確認中..."
    
    if command -v nvidia-smi &> /dev/null; then
        log_info "NVIDIA GPUが検出されました"
        
        # NVIDIA Container Toolkit確認
        if podman info --format json | jq -r '.host.ociRuntime.name' | grep -q nvidia; then
            log_info "NVIDIA Container Toolkitが設定されています"
        else
            log_warn "NVIDIA Container Toolkitが設定されていません"
            log_warn "GPU機能を使用するには以下を実行してください:"
            log_warn "sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml"
        fi
    else
        log_info "GPUは検出されませんでした（CPU専用モードで動作します）"
    fi
}

# セットアップ完了確認
verify_setup() {
    log_info "セットアップ検証中..."
    
    # ネットワーク確認
    if podman network exists ai-semble; then
        log_info "✓ ネットワーク 'ai-semble' 存在確認"
    else
        log_error "✗ ネットワーク 'ai-semble' が見つかりません"
        return 1
    fi
    
    # ボリューム確認
    if podman volume exists ai-semble-data && podman volume exists ai-semble-models; then
        log_info "✓ 必要なボリュームの存在確認"
    else
        log_error "✗ 必要なボリュームが見つかりません"
        return 1
    fi
    
    # イメージ確認
    local images=(
        "localhost/ai-semble/orchestrator:latest"
        "localhost/ai-semble/llm:latest"
        "localhost/ai-semble/vision:latest"
        "localhost/ai-semble/nlp:latest"
        "localhost/ai-semble/processor:latest"
    )
    
    for image in "${images[@]}"; do
        if podman image exists "$image"; then
            log_info "✓ イメージ '$image' 存在確認"
        else
            log_error "✗ イメージ '$image' が見つかりません"
            return 1
        fi
    done
    
    log_info "セットアップ検証完了"
}

# メイン実行関数
main() {
    log_info "Ai-semble v2 セットアップを開始します..."
    log_info "ログファイル: $LOG_FILE"
    
    check_prerequisites
    setup_podman
    create_network
    create_volumes
    build_images
    install_quadlets
    check_gpu_setup
    verify_setup
    
    log_info "=== セットアップ完了 ==="
    log_info "次のステップ:"
    log_info "1. Pod開始: systemctl --user start ai-semble.pod"
    log_info "2. 状態確認: podman pod ps"
    log_info "3. ログ確認: journalctl --user -u ai-semble.pod -f"
    log_info "4. API接続: curl http://localhost:8080/health"
}

# エラートラップ
trap 'log_error "セットアップ中にエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"