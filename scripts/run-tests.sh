#!/bin/bash
# テスト実行スクリプト

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-tests.log"

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

# 使用方法表示
usage() {
    cat << EOF
Usage: $0 [TEST_TYPE] [OPTIONS]

Test Types:
    unit            ユニットテストのみ実行
    integration     統合テストのみ実行
    all             全テスト実行 (デフォルト)
    lint            コード品質チェックのみ
    quick           簡易テスト（構文チェック等）

Options:
    -v, --verbose   詳細出力
    -c, --coverage  カバレッジレポート生成
    -h, --help      このヘルプを表示

Examples:
    $0 unit -c              # ユニットテスト + カバレッジ
    $0 integration -v       # 統合テスト + 詳細出力
    $0 lint                 # コード品質チェック
    $0 quick                # 簡易テスト
EOF
}

# Python環境チェック
check_python_env() {
    log_info "Python環境をチェック中..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3が見つかりません"
        exit 1
    fi
    
    # テスト依存関係のインストール
    if [[ ! -d "$PROJECT_ROOT/tests/.venv" ]]; then
        log_info "テスト用仮想環境を作成中..."
        python3 -m venv "$PROJECT_ROOT/tests/.venv"
    fi
    
    source "$PROJECT_ROOT/tests/.venv/bin/activate"
    pip install -q --upgrade pip
    pip install -q -r "$PROJECT_ROOT/tests/requirements.txt"
}

# ユニットテスト実行
run_unit_tests() {
    log_info "=== ユニットテスト実行 ==="
    
    local pytest_args=("tests/unit/")
    
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    if [[ "${COVERAGE:-false}" == "true" ]]; then
        pytest_args+=("--cov=containers" "--cov-report=html" "--cov-report=term")
    fi
    
    cd "$PROJECT_ROOT"
    if python -m pytest "${pytest_args[@]}"; then
        log_success "ユニットテスト完了"
        return 0
    else
        log_error "ユニットテストが失敗しました"
        return 1
    fi
}

# 統合テスト実行
run_integration_tests() {
    log_info "=== 統合テスト実行 ==="
    
    # サービスが起動しているかチェック
    local services_available=true
    
    if ! curl -f http://localhost:8080/health &>/dev/null; then
        log_error "Orchestratorサービスが利用できません"
        log_info "統合テストを実行するには以下を実行してください:"
        log_info "  ./scripts/deploy.sh start"
        services_available=false
    fi
    
    local pytest_args=("tests/integration/")
    
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        pytest_args+=("-v")
    fi
    
    if [[ "$services_available" == "true" ]]; then
        cd "$PROJECT_ROOT"
        if python -m pytest "${pytest_args[@]}"; then
            log_success "統合テスト完了"
            return 0
        else
            log_error "統合テストが失敗しました"
            return 1
        fi
    else
        log_error "統合テストをスキップしました（サービスが利用できません）"
        return 1
    fi
}

# コード品質チェック
run_lint_checks() {
    log_info "=== コード品質チェック ==="
    
    local all_passed=true
    
    # Python構文チェック
    log_info "Python構文チェック中..."
    if find containers/ -name "*.py" -exec python3 -m py_compile {} \; 2>/dev/null; then
        log_success "Python構文チェック完了"
    else
        log_error "Python構文エラーが見つかりました"
        all_passed=false
    fi
    
    # YAML構文チェック
    log_info "YAML構文チェック中..."
    if python3 -c "import yaml; yaml.safe_load_all(open('pods/ai-semble.yaml'))" 2>/dev/null; then
        log_success "YAML構文チェック完了"
    else
        log_error "YAML構文エラーが見つかりました"
        all_passed=false
    fi
    
    # JSON構文チェック
    log_info "JSON構文チェック中..."
    if python3 -c "import json; json.load(open('security/seccomp/ai-semble.json'))" 2>/dev/null; then
        log_success "JSON構文チェック完了"
    else
        log_error "JSON構文エラーが見つかりました"
        all_passed=false
    fi
    
    # Flake8がある場合は実行
    if command -v flake8 &>/dev/null; then
        log_info "Flake8チェック中..."
        if flake8 containers/ --max-line-length=88 --extend-ignore=E203,W503; then
            log_success "Flake8チェック完了"
        else
            log_error "Flake8でエラーが見つかりました"
            all_passed=false
        fi
    fi
    
    if [[ "$all_passed" == "true" ]]; then
        log_success "全てのコード品質チェックが完了しました"
        return 0
    else
        log_error "コード品質チェックで問題が見つかりました"
        return 1
    fi
}

# 簡易テスト
run_quick_tests() {
    log_info "=== 簡易テスト実行 ==="
    
    cd "$PROJECT_ROOT"
    if python3 test_quick.py; then
        log_success "簡易テスト完了"
        return 0
    else
        log_error "簡易テストが失敗しました"
        return 1
    fi
}

# 全テスト実行
run_all_tests() {
    log_info "=== 全テスト実行 ==="
    
    local results=()
    
    run_lint_checks && results+=("lint:PASS") || results+=("lint:FAIL")
    run_unit_tests && results+=("unit:PASS") || results+=("unit:FAIL")
    run_integration_tests && results+=("integration:PASS") || results+=("integration:FAIL")
    
    log_info "=== テスト結果サマリー ==="
    for result in "${results[@]}"; do
        local test_type="${result%:*}"
        local status="${result#*:}"
        if [[ "$status" == "PASS" ]]; then
            log_success "$test_type: $status"
        else
            log_error "$test_type: $status"
        fi
    done
    
    # 全てPASSかチェック
    if [[ "${results[*]}" =~ "FAIL" ]]; then
        log_error "一部のテストが失敗しました"
        return 1
    else
        log_success "全てのテストが成功しました"
        return 0
    fi
}

# メイン実行関数
main() {
    local test_type="${1:-all}"
    shift || true
    
    # オプション解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                ;;
            -c|--coverage)
                COVERAGE=true
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                usage
                exit 1
                ;;
        esac
        shift
    done
    
    log_info "Ai-semble v2 テスト実行開始: $test_type"
    log_info "ログファイル: $LOG_FILE"
    
    check_python_env
    
    case "$test_type" in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        lint)
            run_lint_checks
            ;;
        quick)
            run_quick_tests
            ;;
        all)
            run_all_tests
            ;;
        *)
            log_error "不明なテストタイプ: $test_type"
            usage
            exit 1
            ;;
    esac
}

# エラートラップ
trap 'log_error "テスト実行中にエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"