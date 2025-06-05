#!/bin/bash
# 基本動作確認スクリプト

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-test-basic.log"

# ログ関数
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE" >&2
}

log_success() {
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

# テスト結果カウンター
total_tests=0
passed_tests=0
failed_tests=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((total_tests++))
    log_info "Testing: $test_name"
    
    if eval "$test_command" >> "$LOG_FILE" 2>&1; then
        ((passed_tests++))
        log_success "✓ $test_name"
        return 0
    else
        ((failed_tests++))
        log_error "✗ $test_name"
        return 1
    fi
}

# 1. ディレクトリ構造確認
test_directory_structure() {
    log_info "=== ディレクトリ構造確認 ==="
    
    local required_dirs=(
        "containers/orchestrator"
        "containers/ai-services/llm" 
        "containers/data-processor"
        "pods"
        "quadlets"
        "scripts"
        "security"
    )
    
    for dir in "${required_dirs[@]}"; do
        run_test "Directory exists: $dir" "test -d '$PROJECT_ROOT/$dir'"
    done
}

# 2. 必要ファイル確認
test_required_files() {
    log_info "=== 必要ファイル確認 ==="
    
    local required_files=(
        "containers/orchestrator/Containerfile"
        "containers/orchestrator/requirements.txt"
        "containers/orchestrator/src/app.py"
        "containers/ai-services/llm/Containerfile"
        "containers/data-processor/Containerfile"
        "pods/ai-semble.yaml"
        "quadlets/ai-semble.pod"
        "scripts/setup.sh"
        "scripts/deploy.sh"
    )
    
    for file in "${required_files[@]}"; do
        run_test "File exists: $file" "test -f '$PROJECT_ROOT/$file'"
    done
}

# 3. Python構文チェック
test_python_syntax() {
    log_info "=== Python構文チェック ==="
    
    # Orchestrator
    run_test "Orchestrator Python syntax" "cd '$PROJECT_ROOT/containers/orchestrator/src' && python -m py_compile app.py"
    run_test "Health API syntax" "cd '$PROJECT_ROOT/containers/orchestrator/src' && python -m py_compile api/health.py"
    run_test "AI API syntax" "cd '$PROJECT_ROOT/containers/orchestrator/src' && python -m py_compile api/ai.py"
    run_test "Jobs API syntax" "cd '$PROJECT_ROOT/containers/orchestrator/src' && python -m py_compile api/jobs.py"
    run_test "Settings syntax" "cd '$PROJECT_ROOT/containers/orchestrator/src' && python -m py_compile config/settings.py"
    
    # LLM Service
    run_test "LLM Service syntax" "cd '$PROJECT_ROOT/containers/ai-services/llm/src' && python -m py_compile llm_service.py"
    
    # Data Processor
    run_test "Data Processor syntax" "cd '$PROJECT_ROOT/containers/data-processor/src' && python -m py_compile processor_service.py"
}

# 4. YAML構文チェック
test_yaml_syntax() {
    log_info "=== YAML構文チェック ==="
    
    if command -v python3 &> /dev/null; then
        run_test "Pod YAML syntax" "python3 -c 'import yaml; yaml.safe_load(open(\"$PROJECT_ROOT/pods/ai-semble.yaml\"))'"
        run_test "Dev Pod YAML syntax" "python3 -c 'import yaml; yaml.safe_load(open(\"$PROJECT_ROOT/pods/ai-semble-dev.yaml\"))'"
    else
        log_error "Python3 not available, skipping YAML syntax check"
    fi
}

# 5. JSON構文チェック
test_json_syntax() {
    log_info "=== JSON構文チェック ==="
    
    run_test "Seccomp JSON syntax" "python3 -c 'import json; json.load(open(\"$PROJECT_ROOT/security/seccomp/ai-semble.json\"))'"
}

# 6. スクリプト実行権限確認
test_script_permissions() {
    log_info "=== スクリプト実行権限確認 ==="
    
    local scripts=(
        "scripts/setup.sh"
        "scripts/deploy.sh" 
        "scripts/install-security.sh"
    )
    
    for script in "${scripts[@]}"; do
        run_test "Script executable: $script" "test -x '$PROJECT_ROOT/$script'"
    done
}

# 7. コンテナファイル基本確認
test_containerfiles() {
    log_info "=== Containerfile基本確認 ==="
    
    # FROM句の確認
    run_test "Orchestrator FROM" "grep -q '^FROM' '$PROJECT_ROOT/containers/orchestrator/Containerfile'"
    run_test "LLM FROM" "grep -q '^FROM' '$PROJECT_ROOT/containers/ai-services/llm/Containerfile'"
    run_test "Processor FROM" "grep -q '^FROM' '$PROJECT_ROOT/containers/data-processor/Containerfile'"
    
    # EXPOSE句の確認
    run_test "Orchestrator EXPOSE" "grep -q 'EXPOSE 8080' '$PROJECT_ROOT/containers/orchestrator/Containerfile'"
    run_test "LLM EXPOSE" "grep -q 'EXPOSE 8081' '$PROJECT_ROOT/containers/ai-services/llm/Containerfile'"
    run_test "Processor EXPOSE" "grep -q 'EXPOSE 8084' '$PROJECT_ROOT/containers/data-processor/Containerfile'"
}

# 8. 依存関係ファイル確認
test_dependencies() {
    log_info "=== 依存関係ファイル確認 ==="
    
    # requirements.txtの存在と基本内容確認
    run_test "Orchestrator requirements" "test -f '$PROJECT_ROOT/containers/orchestrator/requirements.txt' && grep -q 'fastapi' '$PROJECT_ROOT/containers/orchestrator/requirements.txt'"
    run_test "LLM requirements" "test -f '$PROJECT_ROOT/containers/ai-services/llm/requirements.txt' && grep -q 'torch' '$PROJECT_ROOT/containers/ai-services/llm/requirements.txt'"
    run_test "Processor requirements" "test -f '$PROJECT_ROOT/containers/data-processor/requirements.txt' && grep -q 'pandas' '$PROJECT_ROOT/containers/data-processor/requirements.txt'"
}

# 9. 設定ファイルテスト
test_configurations() {
    log_info "=== 設定ファイルテスト ==="
    
    # Quadlet設定の基本構造確認
    run_test "Pod Quadlet [Unit]" "grep -q '\\[Unit\\]' '$PROJECT_ROOT/quadlets/ai-semble.pod'"
    run_test "Pod Quadlet [Pod]" "grep -q '\\[Pod\\]' '$PROJECT_ROOT/quadlets/ai-semble.pod'"
    run_test "Network Quadlet [Network]" "grep -q '\\[Network\\]' '$PROJECT_ROOT/quadlets/ai-semble.network'"
    run_test "Volume Quadlet [Volume]" "grep -q '\\[Volume\\]' '$PROJECT_ROOT/quadlets/ai-semble-data.volume'"
}

# 10. ドキュメント確認
test_documentation() {
    log_info "=== ドキュメント確認 ==="
    
    run_test "README exists" "test -f '$PROJECT_ROOT/README.md'"
    run_test "CLAUDE.md exists" "test -f '$PROJECT_ROOT/CLAUDE.md'"
    run_test "Development plan exists" "test -f '$PROJECT_ROOT/DEVELOPMENT_PLAN.md'"
    run_test "User experience guide exists" "test -f '$PROJECT_ROOT/docs/USER_EXPERIENCE_GUIDE.md'"
    run_test "API examples exists" "test -f '$PROJECT_ROOT/docs/API_EXAMPLES.md'"
}

# メイン実行関数
main() {
    log_info "Ai-semble v2 基本動作確認を開始します..."
    log_info "ログファイル: $LOG_FILE"
    log_info "プロジェクトディレクトリ: $PROJECT_ROOT"
    
    # 各テスト実行
    test_directory_structure
    test_required_files
    test_python_syntax
    test_yaml_syntax
    test_json_syntax
    test_script_permissions
    test_containerfiles
    test_dependencies
    test_configurations
    test_documentation
    
    # 結果サマリー
    log_info "=== テスト結果サマリー ==="
    log_info "総テスト数: $total_tests"
    log_success "成功: $passed_tests"
    
    if [[ $failed_tests -gt 0 ]]; then
        log_error "失敗: $failed_tests"
        log_error "詳細は $LOG_FILE を確認してください"
        exit 1
    else
        log_success "全てのテストが成功しました！"
        log_info "次のステップ:"
        log_info "1. Podmanが利用可能か確認: podman --version"
        log_info "2. セットアップ実行: ./scripts/setup.sh"
        log_info "3. Pod起動: ./scripts/deploy.sh start"
    fi
}

# エラートラップ
trap 'log_error "テスト中にエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"