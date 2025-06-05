#!/bin/bash
# Ai-semble v2 実環境診断スクリプト

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-diagnosis.log"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE" >&2
}

# 診断結果カウンター
total_checks=0
passed_checks=0
failed_checks=0
warning_checks=0

# テスト結果記録
record_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    ((total_checks++))
    
    case "$result" in
        "PASS")
            ((passed_checks++))
            log_success "✓ $test_name: $message"
            ;;
        "FAIL")
            ((failed_checks++))
            log_error "✗ $test_name: $message"
            ;;
        "WARN")
            ((warning_checks++))
            log_warning "⚠ $test_name: $message"
            ;;
    esac
}

# システム環境診断
diagnose_system() {
    log_info "=== システム環境診断 ==="
    
    # OS確認
    if command -v lsb_release &>/dev/null; then
        os_info=$(lsb_release -d | cut -f2-)
        record_result "OS Version" "PASS" "$os_info"
    elif [[ -f /etc/os-release ]]; then
        os_info=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
        record_result "OS Version" "PASS" "$os_info"
    else
        record_result "OS Version" "WARN" "OS情報を取得できませんでした"
    fi
    
    # CPU確認
    cpu_cores=$(nproc)
    if [[ $cpu_cores -ge 4 ]]; then
        record_result "CPU Cores" "PASS" "${cpu_cores} cores (推奨: 4+ cores)"
    else
        record_result "CPU Cores" "WARN" "${cpu_cores} cores (推奨: 4+ cores)"
    fi
    
    # メモリ確認
    mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $mem_gb -ge 16 ]]; then
        record_result "Memory" "PASS" "${mem_gb}GB (推奨: 16GB+)"
    elif [[ $mem_gb -ge 8 ]]; then
        record_result "Memory" "WARN" "${mem_gb}GB (推奨: 16GB+)"
    else
        record_result "Memory" "FAIL" "${mem_gb}GB (最低限: 8GB)"
    fi
    
    # ディスク容量確認
    disk_free=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $disk_free -ge 50 ]]; then
        record_result "Disk Space" "PASS" "${disk_free}GB free (推奨: 50GB+)"
    elif [[ $disk_free -ge 20 ]]; then
        record_result "Disk Space" "WARN" "${disk_free}GB free (推奨: 50GB+)"
    else
        record_result "Disk Space" "FAIL" "${disk_free}GB free (最低限: 20GB)"
    fi
}

# Podman環境診断
diagnose_podman() {
    log_info "=== Podman環境診断 ==="
    
    # Podman存在確認
    if command -v podman &>/dev/null; then
        podman_version=$(podman --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
        record_result "Podman Installation" "PASS" "version $podman_version"
    else
        record_result "Podman Installation" "FAIL" "Podmanがインストールされていません"
        return
    fi
    
    # Podman設定確認
    if podman info &>/dev/null; then
        record_result "Podman Configuration" "PASS" "正常に設定されています"
    else
        record_result "Podman Configuration" "FAIL" "Podman設定に問題があります"
    fi
    
    # Rootless確認
    if podman info --format="{{.Host.Security.Rootless}}" 2>/dev/null | grep -q true; then
        record_result "Rootless Mode" "PASS" "Rootlessモードで動作中"
    else
        record_result "Rootless Mode" "WARN" "Rootlessモードが無効です"
    fi
    
    # systemd統合確認
    if systemctl --user status podman.socket &>/dev/null; then
        record_result "systemd Integration" "PASS" "systemd統合が有効です"
    else
        record_result "systemd Integration" "WARN" "systemd統合が無効です"
    fi
    
    # ユーザー名前空間確認
    if grep -q "^$(whoami):" /etc/subuid 2>/dev/null; then
        record_result "User Namespaces" "PASS" "ユーザー名前空間が設定済み"
    else
        record_result "User Namespaces" "FAIL" "ユーザー名前空間の設定が必要です"
    fi
}

# セキュリティ環境診断
diagnose_security() {
    log_info "=== セキュリティ環境診断 ==="
    
    # SELinux確認
    if command -v getenforce &>/dev/null; then
        selinux_status=$(getenforce)
        if [[ "$selinux_status" == "Enforcing" ]]; then
            record_result "SELinux" "PASS" "Enforcing mode"
        elif [[ "$selinux_status" == "Permissive" ]]; then
            record_result "SELinux" "WARN" "Permissive mode (本番では非推奨)"
        else
            record_result "SELinux" "WARN" "Disabled (セキュリティ上推奨されません)"
        fi
    else
        record_result "SELinux" "WARN" "SELinuxが利用できません"
    fi
    
    # ファイアウォール確認
    if command -v firewall-cmd &>/dev/null; then
        if firewall-cmd --state &>/dev/null; then
            record_result "Firewall" "PASS" "firewalld が動作中"
        else
            record_result "Firewall" "WARN" "firewalld が停止中"
        fi
    elif command -v ufw &>/dev/null; then
        if ufw status | grep -q "Status: active"; then
            record_result "Firewall" "PASS" "ufw が有効"
        else
            record_result "Firewall" "WARN" "ufw が無効"
        fi
    else
        record_result "Firewall" "WARN" "ファイアウォールが検出されません"
    fi
    
    # Seccompプロファイル確認
    if [[ -f /etc/containers/seccomp/ai-semble.json ]]; then
        record_result "Seccomp Profile" "PASS" "カスタムSeccompプロファイルが設置済み"
    else
        record_result "Seccomp Profile" "WARN" "カスタムSeccompプロファイルが未設置"
    fi
}

# ネットワーク診断
diagnose_network() {
    log_info "=== ネットワーク診断 ==="
    
    # Podmanネットワーク確認
    if podman network exists ai-semble 2>/dev/null; then
        record_result "Podman Network" "PASS" "ai-semble ネットワークが存在"
    else
        record_result "Podman Network" "WARN" "ai-semble ネットワークが未作成"
    fi
    
    # ポート利用状況確認
    local ports=(8080 8081 8082 8083 8084)
    local port_conflicts=()
    
    for port in "${ports[@]}"; do
        if ss -tuln | grep -q ":$port "; then
            port_conflicts+=("$port")
        fi
    done
    
    if [[ ${#port_conflicts[@]} -eq 0 ]]; then
        record_result "Port Availability" "PASS" "必要なポート (8080-8084) が利用可能"
    else
        record_result "Port Availability" "WARN" "ポート競合: ${port_conflicts[*]}"
    fi
    
    # DNS解決確認
    if nslookup google.com &>/dev/null; then
        record_result "DNS Resolution" "PASS" "DNS解決が正常"
    else
        record_result "DNS Resolution" "FAIL" "DNS解決に問題があります"
    fi
}

# GPU環境診断
diagnose_gpu() {
    log_info "=== GPU環境診断 ==="
    
    # NVIDIA GPU確認
    if command -v nvidia-smi &>/dev/null; then
        if nvidia-smi &>/dev/null; then
            gpu_count=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits | head -1)
            record_result "NVIDIA GPU" "PASS" "${gpu_count} GPU(s) detected"
        else
            record_result "NVIDIA GPU" "FAIL" "NVIDIA GPUドライバーに問題があります"
        fi
    else
        record_result "NVIDIA GPU" "WARN" "NVIDIA GPUが検出されません (オプション)"
    fi
    
    # NVIDIA Container Toolkit確認
    if [[ -f /etc/cdi/nvidia.yaml ]]; then
        record_result "NVIDIA CDI" "PASS" "NVIDIA CDI設定が存在"
    else
        record_result "NVIDIA CDI" "WARN" "NVIDIA CDI設定が未設置"
    fi
    
    # crun確認 (GPU使用時推奨)
    if command -v crun &>/dev/null; then
        record_result "crun Runtime" "PASS" "crun が利用可能"
    else
        record_result "crun Runtime" "WARN" "crun が未インストール (GPU使用時推奨)"
    fi
}

# Ai-semble固有診断
diagnose_ai_semble() {
    log_info "=== Ai-semble固有診断 ==="
    
    # プロジェクト構造確認
    local required_files=(
        "scripts/setup.sh"
        "scripts/deploy.sh"
        "containers/orchestrator/Containerfile"
        "pods/ai-semble.yaml"
        "quadlets/ai-semble.pod"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        record_result "Project Structure" "PASS" "必要なファイルが全て存在"
    else
        record_result "Project Structure" "FAIL" "不足ファイル: ${missing_files[*]}"
    fi
    
    # Quadlet設定確認
    if [[ -d ~/.config/containers/systemd ]]; then
        quadlet_count=$(find ~/.config/containers/systemd -name "*.pod" -o -name "*.network" -o -name "*.volume" | wc -l)
        if [[ $quadlet_count -gt 0 ]]; then
            record_result "Quadlet Configuration" "PASS" "${quadlet_count} Quadlet設定ファイルが配置済み"
        else
            record_result "Quadlet Configuration" "WARN" "Quadlet設定ファイルが未配置"
        fi
    else
        record_result "Quadlet Configuration" "WARN" "Quadlet設定ディレクトリが未作成"
    fi
    
    # ボリューム確認
    local volumes=(ai-semble-data ai-semble-models)
    local missing_volumes=()
    
    for volume in "${volumes[@]}"; do
        if ! podman volume exists "$volume" 2>/dev/null; then
            missing_volumes+=("$volume")
        fi
    done
    
    if [[ ${#missing_volumes[@]} -eq 0 ]]; then
        record_result "Podman Volumes" "PASS" "必要なボリュームが存在"
    else
        record_result "Podman Volumes" "WARN" "不足ボリューム: ${missing_volumes[*]}"
    fi
}

# サービス状態診断
diagnose_services() {
    log_info "=== サービス状態診断 ==="
    
    # Pod状態確認
    if podman pod exists ai-semble 2>/dev/null; then
        pod_status=$(podman pod ps --filter name=ai-semble --format "{{.Status}}")
        if [[ "$pod_status" == "Running" ]]; then
            record_result "Pod Status" "PASS" "ai-semble Pod が稼働中"
        else
            record_result "Pod Status" "WARN" "ai-semble Pod status: $pod_status"
        fi
    else
        record_result "Pod Status" "WARN" "ai-semble Pod が存在しません"
    fi
    
    # コンテナ状態確認
    if podman ps --filter "pod=ai-semble" --format "{{.Names}}" 2>/dev/null | wc -l | grep -q "5"; then
        record_result "Container Count" "PASS" "5つのコンテナが稼働中"
    else
        container_count=$(podman ps --filter "pod=ai-semble" --format "{{.Names}}" 2>/dev/null | wc -l)
        record_result "Container Count" "WARN" "${container_count}/5 コンテナが稼働中"
    fi
    
    # ヘルスチェック
    local services=(
        "http://localhost:8080/health:Orchestrator"
        "http://localhost:8081/health:LLM"
        "http://localhost:8082/health:Vision"
        "http://localhost:8083/health:NLP"
        "http://localhost:8084/health:Processor"
    )
    
    for service in "${services[@]}"; do
        local url="${service%:*}"
        local name="${service#*:}"
        
        if curl -f -s "$url" &>/dev/null; then
            record_result "$name Health" "PASS" "ヘルスチェック成功"
        else
            record_result "$name Health" "WARN" "ヘルスチェック失敗またはサービス停止中"
        fi
    done
}

# 推奨事項表示
show_recommendations() {
    log_info "=== 推奨事項 ==="
    
    # 失敗項目に基づく推奨事項
    if [[ $failed_checks -gt 0 ]]; then
        log_error "重要な問題が検出されました。以下を確認してください:"
        echo "  - システム要件の確認"
        echo "  - 必要パッケージのインストール"
        echo "  - 設定ファイルの確認"
    fi
    
    if [[ $warning_checks -gt 0 ]]; then
        log_warning "改善可能な項目が検出されました:"
        echo "  - セキュリティ設定の強化"
        echo "  - GPU環境の設定"
        echo "  - ネットワーク設定の最適化"
    fi
    
    # 次のステップ
    log_info "次のステップ:"
    echo "  1. ./scripts/setup.sh      # 初期セットアップ"
    echo "  2. ./scripts/deploy.sh start  # サービス起動"
    echo "  3. ./scripts/run-tests.sh integration  # 統合テスト"
}

# メイン実行関数
main() {
    log_info "Ai-semble v2 実環境診断を開始します..."
    log_info "ログファイル: $LOG_FILE"
    log_info "診断対象: $(hostname) ($(whoami))"
    
    # 各診断実行
    diagnose_system
    diagnose_podman
    diagnose_security
    diagnose_network
    diagnose_gpu
    diagnose_ai_semble
    diagnose_services
    
    # 結果サマリー
    log_info "=== 診断結果サマリー ==="
    log_info "総チェック数: $total_checks"
    log_success "成功: $passed_checks"
    log_warning "警告: $warning_checks"
    log_error "失敗: $failed_checks"
    
    # スコア計算
    local score=$((passed_checks * 100 / total_checks))
    log_info "診断スコア: ${score}%"
    
    if [[ $score -ge 90 ]]; then
        log_success "優秀! 本番運用準備が整っています"
    elif [[ $score -ge 70 ]]; then
        log_warning "良好ですが、いくつかの改善余地があります"
    elif [[ $score -ge 50 ]]; then
        log_warning "基本的な要件は満たしていますが、多くの改善が必要です"
    else
        log_error "重要な問題があります。セットアップを見直してください"
    fi
    
    show_recommendations
    
    # 終了コード決定
    if [[ $failed_checks -gt 0 ]]; then
        exit 1
    elif [[ $warning_checks -gt 0 ]]; then
        exit 2
    else
        exit 0
    fi
}

# エラートラップ
trap 'log_error "診断中にエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"