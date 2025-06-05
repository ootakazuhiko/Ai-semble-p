#!/bin/bash
# Ai-semble v2 デプロイスクリプト

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/tmp/ai-semble-deploy.log"

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

# 使用方法表示
usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start       Pod を開始
    stop        Pod を停止
    restart     Pod を再起動
    status      Pod の状態確認
    logs        Pod のログ表示
    health      ヘルスチェック実行
    update      イメージ更新とPod再起動

Options:
    -h, --help  このヘルプメッセージを表示
    -f, --follow ログをフォロー（logsコマンド用）
    -d, --dev   開発環境Pod使用

Examples:
    $0 start                # 本番Podを開始
    $0 start --dev          # 開発Podを開始
    $0 logs --follow        # ログをリアルタイム表示
    $0 health               # ヘルスチェック実行
EOF
}

# Pod名決定
get_pod_name() {
    if [[ "${DEV_MODE:-false}" == "true" ]]; then
        echo "ai-semble-dev"
    else
        echo "ai-semble"
    fi
}

# Podサービス名決定
get_pod_service() {
    if [[ "${DEV_MODE:-false}" == "true" ]]; then
        echo "ai-semble-dev.pod"
    else
        echo "ai-semble.pod"
    fi
}

# Pod開始
start_pod() {
    local pod_service
    pod_service=$(get_pod_service)
    
    log_info "Pod開始中: $pod_service"
    
    # Quadletサービス開始
    systemctl --user start "$pod_service"
    
    # 開始確認
    local retry_count=0
    local max_retries=30
    
    while [[ $retry_count -lt $max_retries ]]; do
        if systemctl --user is-active --quiet "$pod_service"; then
            log_info "Pod '$pod_service' が正常に開始されました"
            return 0
        fi
        
        log_info "Pod開始を待機中... ($((retry_count + 1))/$max_retries)"
        sleep 5
        ((retry_count++))
    done
    
    log_error "Pod開始がタイムアウトしました"
    return 1
}

# Pod停止
stop_pod() {
    local pod_service
    pod_service=$(get_pod_service)
    
    log_info "Pod停止中: $pod_service"
    
    systemctl --user stop "$pod_service"
    
    # 停止確認
    local retry_count=0
    local max_retries=10
    
    while [[ $retry_count -lt $max_retries ]]; do
        if ! systemctl --user is-active --quiet "$pod_service"; then
            log_info "Pod '$pod_service' が正常に停止されました"
            return 0
        fi
        
        log_info "Pod停止を待機中... ($((retry_count + 1))/$max_retries)"
        sleep 3
        ((retry_count++))
    done
    
    log_warn "Pod停止がタイムアウトしました。強制停止を試行します"
    systemctl --user kill "$pod_service"
    return 1
}

# Pod再起動
restart_pod() {
    log_info "Pod再起動中..."
    stop_pod
    sleep 5
    start_pod
}

# Pod状態確認
show_status() {
    local pod_name
    pod_name=$(get_pod_name)
    
    log_info "Pod状態を確認中: $pod_name"
    
    echo "=== systemd サービス状態 ==="
    systemctl --user status "$(get_pod_service)" --no-pager || true
    
    echo -e "\n=== Pod 状態 ==="
    podman pod ps --filter "name=$pod_name" || true
    
    echo -e "\n=== コンテナ状態 ==="
    podman ps --pod --filter "pod=$pod_name" || true
    
    echo -e "\n=== ネットワーク状態 ==="
    podman network ls --filter "name=ai-semble" || true
    
    echo -e "\n=== ボリューム状態 ==="
    podman volume ls --filter "label=app=ai-semble" || true
}

# ログ表示
show_logs() {
    local pod_service
    pod_service=$(get_pod_service)
    
    local follow_flag=""
    if [[ "${FOLLOW_LOGS:-false}" == "true" ]]; then
        follow_flag="-f"
    fi
    
    log_info "Pod ログ表示: $pod_service"
    journalctl --user -u "$pod_service" $follow_flag --no-pager
}

# ヘルスチェック
health_check() {
    log_info "ヘルスチェック実行中..."
    
    local endpoints=(
        "http://localhost:8080/health"
        "http://localhost:8081/health"
        "http://localhost:8084/health"
    )
    
    local all_healthy=true
    
    for endpoint in "${endpoints[@]}"; do
        log_info "チェック中: $endpoint"
        
        if curl -f -s --max-time 10 "$endpoint" > /dev/null; then
            log_info "✓ $endpoint - 正常"
        else
            log_error "✗ $endpoint - 異常"
            all_healthy=false
        fi
    done
    
    if [[ "$all_healthy" == "true" ]]; then
        log_info "すべてのサービスが正常です"
        return 0
    else
        log_error "一部のサービスに問題があります"
        return 1
    fi
}

# イメージ更新
update_images() {
    local project_root
    project_root="$(dirname "$SCRIPT_DIR")"
    
    log_info "イメージ更新中..."
    
    # Pod停止
    stop_pod
    
    # イメージ再ビルド
    log_info "Orchestratorイメージを再ビルド中..."
    podman build -t localhost/ai-semble/orchestrator:latest "$project_root/containers/orchestrator"
    
    log_info "LLM Serviceイメージを再ビルド中..."
    podman build -t localhost/ai-semble/llm:latest "$project_root/containers/ai-services/llm"
    
    log_info "Data Processorイメージを再ビルド中..."
    podman build -t localhost/ai-semble/processor:latest "$project_root/containers/data-processor"
    
    # Pod再開
    start_pod
    
    log_info "イメージ更新完了"
}

# メイン処理
main() {
    local command="${1:-}"
    shift || true
    
    # オプション解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--follow)
                FOLLOW_LOGS=true
                ;;
            -d|--dev)
                DEV_MODE=true
                ;;
            *)
                log_error "不明なオプション: $1"
                usage
                exit 1
                ;;
        esac
        shift
    done
    
    # コマンド実行
    case "$command" in
        start)
            start_pod
            ;;
        stop)
            stop_pod
            ;;
        restart)
            restart_pod
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        health)
            health_check
            ;;
        update)
            update_images
            ;;
        ""|help)
            usage
            ;;
        *)
            log_error "不明なコマンド: $command"
            usage
            exit 1
            ;;
    esac
}

# エラートラップ
trap 'log_error "デプロイ処理中にエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"