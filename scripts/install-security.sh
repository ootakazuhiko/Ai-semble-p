#!/bin/bash
# Ai-semble v2 セキュリティ設定インストールスクリプト

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-security-install.log"

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

# 管理者権限チェック
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        log_error "このスクリプトは管理者権限で実行してください"
        exit 1
    fi
}

# SELinux状態確認
check_selinux() {
    if ! command -v getenforce &> /dev/null; then
        log_warn "SELinuxが利用できません。SELinux設定をスキップします"
        return 1
    fi
    
    local selinux_status
    selinux_status=$(getenforce)
    
    if [[ "$selinux_status" == "Disabled" ]]; then
        log_warn "SELinuxが無効化されています。SELinux設定をスキップします"
        return 1
    fi
    
    log_info "SELinux状態: $selinux_status"
    return 0
}

# SELinuxポリシーインストール
install_selinux_policy() {
    if ! check_selinux; then
        return 0
    fi
    
    log_info "SELinuxポリシーをインストール中..."
    
    local selinux_dir="$PROJECT_ROOT/security/selinux"
    local policy_name="ai_semble"
    
    # ポリシーファイルの存在確認
    if [[ ! -f "$selinux_dir/${policy_name}.te" ]]; then
        log_error "SELinuxポリシーファイルが見つかりません: $selinux_dir/${policy_name}.te"
        return 1
    fi
    
    # 一時ディレクトリでポリシーコンパイル
    local temp_dir
    temp_dir=$(mktemp -d)
    
    # ファイルをコピー
    cp "$selinux_dir/${policy_name}.te" "$temp_dir/"
    if [[ -f "$selinux_dir/${policy_name}.fc" ]]; then
        cp "$selinux_dir/${policy_name}.fc" "$temp_dir/"
    fi
    
    pushd "$temp_dir" > /dev/null
    
    # ポリシーコンパイル
    log_info "SELinuxポリシーをコンパイル中..."
    if ! make -f /usr/share/selinux/devel/Makefile "${policy_name}.pp"; then
        log_error "SELinuxポリシーのコンパイルに失敗しました"
        popd > /dev/null
        rm -rf "$temp_dir"
        return 1
    fi
    
    # ポリシーインストール
    log_info "SELinuxポリシーをインストール中..."
    if ! semodule -i "${policy_name}.pp"; then
        log_error "SELinuxポリシーのインストールに失敗しました"
        popd > /dev/null
        rm -rf "$temp_dir"
        return 1
    fi
    
    popd > /dev/null
    rm -rf "$temp_dir"
    
    # ファイルコンテキスト復元
    if [[ -f "$selinux_dir/${policy_name}.fc" ]]; then
        log_info "ファイルコンテキストを復元中..."
        restorecon -R /var/lib/containers/storage/volumes/ 2>/dev/null || true
        restorecon -R /home/*/\\.local/share/containers/storage/volumes/ 2>/dev/null || true
    fi
    
    log_info "SELinuxポリシーのインストールが完了しました"
}

# Seccompプロファイル配置
install_seccomp_profile() {
    log_info "Seccompプロファイルを配置中..."
    
    local seccomp_dir="$PROJECT_ROOT/security/seccomp"
    local system_seccomp_dir="/etc/containers/seccomp"
    
    # システムディレクトリ作成
    mkdir -p "$system_seccomp_dir"
    
    # プロファイルファイルをコピー
    if [[ -f "$seccomp_dir/ai-semble.json" ]]; then
        cp "$seccomp_dir/ai-semble.json" "$system_seccomp_dir/"
        chmod 644 "$system_seccomp_dir/ai-semble.json"
        log_info "Seccompプロファイルを配置しました: $system_seccomp_dir/ai-semble.json"
    else
        log_error "Seccompプロファイルが見つかりません: $seccomp_dir/ai-semble.json"
        return 1
    fi
}

# ファイアウォール設定
configure_firewall() {
    log_info "ファイアウォール設定を確認中..."
    
    if command -v firewall-cmd &> /dev/null; then
        log_info "firewalldを設定中..."
        
        # AI-semble用ポートを開放
        local ports=(8080 8081 8082 8083 8084)
        
        for port in "${ports[@]}"; do
            if firewall-cmd --quiet --query-port="${port}/tcp"; then
                log_info "ポート ${port}/tcp は既に開放されています"
            else
                firewall-cmd --permanent --add-port="${port}/tcp"
                log_info "ポート ${port}/tcp を開放しました"
            fi
        done
        
        # 設定をリロード
        firewall-cmd --reload
        log_info "ファイアウォール設定を適用しました"
        
    elif command -v ufw &> /dev/null; then
        log_info "ufwを設定中..."
        
        local ports=(8080 8081 8082 8083 8084)
        
        for port in "${ports[@]}"; do
            ufw allow "${port}/tcp"
            log_info "ポート ${port}/tcp を開放しました"
        done
        
    else
        log_warn "サポートされているファイアウォール管理ツールが見つかりません"
        log_warn "手動でポート 8080-8084/tcp を開放してください"
    fi
}

# AppArmor設定（Ubuntu/Debian用）
configure_apparmor() {
    if ! command -v aa-status &> /dev/null; then
        log_info "AppArmorは利用できません。スキップします"
        return 0
    fi
    
    log_info "AppArmor設定を確認中..."
    
    # Podman用プロファイルが存在するか確認
    if [[ -f /etc/apparmor.d/usr.bin.podman ]]; then
        log_info "Podman AppArmorプロファイルが存在します"
    else
        log_warn "Podman AppArmorプロファイルが見つかりません"
        log_warn "必要に応じて手動でAppArmorプロファイルを設定してください"
    fi
}

# システムセキュリティ設定
configure_system_security() {
    log_info "システムセキュリティ設定を適用中..."
    
    # カーネルパラメータ設定
    local sysctl_conf="/etc/sysctl.d/99-ai-semble-security.conf"
    
    cat > "$sysctl_conf" << 'EOF'
# Ai-semble セキュリティ設定

# ネットワークセキュリティ
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# コンテナセキュリティ
kernel.unprivileged_userns_clone = 1
user.max_user_namespaces = 28633

# プロセス分離
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
EOF

    # 設定を適用
    sysctl -p "$sysctl_conf"
    
    log_info "システムセキュリティ設定を適用しました: $sysctl_conf"
}

# 設定検証
verify_security_setup() {
    log_info "セキュリティ設定を検証中..."
    
    local all_ok=true
    
    # SELinux確認
    if check_selinux; then
        if semodule -l | grep -q ai_semble; then
            log_info "✓ SELinuxポリシー 'ai_semble' がインストールされています"
        else
            log_error "✗ SELinuxポリシー 'ai_semble' が見つかりません"
            all_ok=false
        fi
    fi
    
    # Seccompプロファイル確認
    if [[ -f /etc/containers/seccomp/ai-semble.json ]]; then
        log_info "✓ Seccompプロファイルが配置されています"
    else
        log_error "✗ Seccompプロファイルが見つかりません"
        all_ok=false
    fi
    
    # ファイアウォール確認
    if command -v firewall-cmd &> /dev/null; then
        if firewall-cmd --quiet --query-port=8080/tcp; then
            log_info "✓ ファイアウォールポートが開放されています"
        else
            log_warn "⚠ ファイアウォールポートが開放されていない可能性があります"
        fi
    fi
    
    if [[ "$all_ok" == "true" ]]; then
        log_info "セキュリティ設定の検証が完了しました"
        return 0
    else
        log_error "セキュリティ設定に問題があります"
        return 1
    fi
}

# メイン実行関数
main() {
    log_info "Ai-semble v2 セキュリティ設定インストールを開始します..."
    log_info "ログファイル: $LOG_FILE"
    
    check_sudo
    install_selinux_policy
    install_seccomp_profile
    configure_firewall
    configure_apparmor
    configure_system_security
    verify_security_setup
    
    log_info "=== セキュリティ設定インストール完了 ==="
    log_info "次のステップ:"
    log_info "1. システムを再起動することを推奨します"
    log_info "2. 通常ユーザーでセットアップスクリプトを実行してください"
    log_info "3. ./scripts/setup.sh"
}

# エラートラップ
trap 'log_error "セキュリティ設定中にエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"