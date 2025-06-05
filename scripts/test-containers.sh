#!/bin/bash
# Container Build and Testing Script for Ai-semble v2
# Tests all container builds and basic functionality

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-container-test.log"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Test results tracking
total_tests=0
passed_tests=0
failed_tests=0

# Logging functions
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

# Test execution function
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

# Check container runtime
check_container_runtime() {
    log_info "=== Checking Container Runtime ==="
    
    if command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
        log_success "Using Podman"
        run_test "Podman version" "$CONTAINER_CMD --version"
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
        log_success "Using Docker"
        run_test "Docker version" "$CONTAINER_CMD --version"
    else
        log_error "No container runtime found (podman or docker required)"
        exit 1
    fi
    
    # Test basic container functionality
    run_test "Container runtime connectivity" "$CONTAINER_CMD info > /dev/null"
}

# Build container image
build_container() {
    local container_name="$1"
    local container_path="$2"
    
    log_info "Building container: $container_name"
    
    local image_tag="localhost/ai-semble/$container_name:test"
    
    if cd "$PROJECT_ROOT/$container_path" && \
       $CONTAINER_CMD build -t "$image_tag" . --quiet; then
        log_success "Built $container_name successfully"
        return 0
    else
        log_error "Failed to build $container_name"
        return 1
    fi
}

# Test container startup
test_container_startup() {
    local container_name="$1"
    local image_tag="localhost/ai-semble/$container_name:test"
    
    log_info "Testing startup: $container_name"
    
    # Run container in background with basic health check
    local container_id=""
    
    case "$container_name" in
        "orchestrator")
            container_id=$($CONTAINER_CMD run -d -p 8080:8080 "$image_tag" 2>/dev/null || echo "")
            ;;
        "llm")
            container_id=$($CONTAINER_CMD run -d -p 8081:8081 "$image_tag" 2>/dev/null || echo "")
            ;;
        "nlp")
            container_id=$($CONTAINER_CMD run -d -p 8083:8083 "$image_tag" 2>/dev/null || echo "")
            ;;
        "vision")
            container_id=$($CONTAINER_CMD run -d -p 8082:8082 "$image_tag" 2>/dev/null || echo "")
            ;;
        "data-processor")
            container_id=$($CONTAINER_CMD run -d -p 8084:8084 "$image_tag" 2>/dev/null || echo "")
            ;;
    esac
    
    if [[ -n "$container_id" ]]; then
        # Wait a moment for startup
        sleep 3
        
        # Check if container is still running
        if $CONTAINER_CMD ps | grep -q "$container_id"; then
            log_success "Container $container_name started successfully"
            
            # Clean up
            $CONTAINER_CMD stop "$container_id" > /dev/null 2>&1
            $CONTAINER_CMD rm "$container_id" > /dev/null 2>&1
            
            return 0
        else
            log_error "Container $container_name failed to stay running"
            
            # Show logs for debugging
            $CONTAINER_CMD logs "$container_id" 2>&1 | tail -10 >> "$LOG_FILE"
            $CONTAINER_CMD rm "$container_id" > /dev/null 2>&1
            
            return 1
        fi
    else
        log_error "Failed to start container $container_name"
        return 1
    fi
}

# Test all containers
test_all_containers() {
    log_info "=== Testing All Container Builds ==="
    
    local containers=(
        "orchestrator:containers/orchestrator"
        "llm:containers/ai-services/llm"
        "nlp:containers/ai-services/nlp"
        "vision:containers/ai-services/vision"
        "data-processor:containers/data-processor"
    )
    
    for container_spec in "${containers[@]}"; do
        local container_name="${container_spec%:*}"
        local container_path="${container_spec#*:}"
        
        # Check if container directory exists
        if [[ ! -d "$PROJECT_ROOT/$container_path" ]]; then
            log_warning "Container directory not found: $container_path"
            continue
        fi
        
        # Build container
        if run_test "Build $container_name" "build_container '$container_name' '$container_path'"; then
            # Test startup if build succeeded
            run_test "Startup $container_name" "test_container_startup '$container_name'"
        fi
    done
}

# Test pod configuration
test_pod_configuration() {
    log_info "=== Testing Pod Configuration ==="
    
    local pod_files=(
        "pods/ai-semble.yaml"
        "pods/ai-semble-dev.yaml"
    )
    
    for pod_file in "${pod_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$pod_file" ]]; then
            run_test "YAML syntax: $pod_file" "python3 -c \"import yaml; yaml.safe_load_all(open('$PROJECT_ROOT/$pod_file'))\""
            
            # Test with container runtime if supported
            if [[ "$CONTAINER_CMD" == "podman" ]]; then
                run_test "Pod validation: $pod_file" "$CONTAINER_CMD play kube '$PROJECT_ROOT/$pod_file' --dry-run"
            fi
        else
            log_warning "Pod file not found: $pod_file"
        fi
    done
}

# Test quadlet configuration
test_quadlet_configuration() {
    log_info "=== Testing Quadlet Configuration ==="
    
    local quadlet_files=(
        "quadlets/ai-semble.pod"
        "quadlets/ai-semble.network"
        "quadlets/ai-semble-data.volume"
        "quadlets/ai-semble-models.volume"
    )
    
    for quadlet_file in "${quadlet_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$quadlet_file" ]]; then
            # Basic syntax validation
            run_test "Quadlet syntax: $quadlet_file" "test -s '$PROJECT_ROOT/$quadlet_file'"
            
            # Check for required sections
            case "$quadlet_file" in
                *.pod)
                    run_test "Pod section in $quadlet_file" "grep -q '\\[Pod\\]' '$PROJECT_ROOT/$quadlet_file'"
                    ;;
                *.network)
                    run_test "Network section in $quadlet_file" "grep -q '\\[Network\\]' '$PROJECT_ROOT/$quadlet_file'"
                    ;;
                *.volume)
                    run_test "Volume section in $quadlet_file" "grep -q '\\[Volume\\]' '$PROJECT_ROOT/$quadlet_file'"
                    ;;
            esac
        else
            log_warning "Quadlet file not found: $quadlet_file"
        fi
    done
}

# Performance and security tests
test_security_compliance() {
    log_info "=== Testing Security Compliance ==="
    
    # Check for security configurations
    run_test "SELinux policy exists" "test -f '$PROJECT_ROOT/security/selinux/ai_semble.te'"
    run_test "Seccomp profile exists" "test -f '$PROJECT_ROOT/security/seccomp/ai-semble.json'"
    
    # Validate seccomp profile
    if [[ -f "$PROJECT_ROOT/security/seccomp/ai-semble.json" ]]; then
        run_test "Seccomp JSON valid" "python3 -c \"import json; json.load(open('$PROJECT_ROOT/security/seccomp/ai-semble.json'))\""
    fi
    
    # Check for hardening script
    run_test "Security hardening script exists" "test -x '$PROJECT_ROOT/security/security-hardening.sh'"
}

# Network connectivity tests
test_network_configuration() {
    log_info "=== Testing Network Configuration ==="
    
    # Test if we can create the network (cleanup afterwards)
    if [[ "$CONTAINER_CMD" == "podman" ]]; then
        if run_test "Create test network" "$CONTAINER_CMD network create ai-semble-test --subnet 10.89.0.0/24"; then
            run_test "Remove test network" "$CONTAINER_CMD network rm ai-semble-test"
        fi
    fi
    
    # Check port availability
    local ports=(8080 8081 8082 8083 8084)
    for port in "${ports[@]}"; do
        if ! netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log_success "Port $port available"
            ((passed_tests++))
        else
            log_warning "Port $port already in use"
        fi
        ((total_tests++))
    done
}

# Cleanup function
cleanup() {
    log_info "=== Cleaning Up Test Artifacts ==="
    
    # Stop and remove any test containers
    if [[ -n "${CONTAINER_CMD:-}" ]]; then
        # Remove test images
        $CONTAINER_CMD rmi $(${CONTAINER_CMD} images -q "localhost/ai-semble/*:test" 2>/dev/null) 2>/dev/null || true
        
        # Clean up any orphaned test containers
        $CONTAINER_CMD container prune -f 2>/dev/null || true
        
        log_info "Cleanup completed"
    fi
}

# Generate test report
generate_report() {
    log_info "=== Generating Test Report ==="
    
    local report_file="$PROJECT_ROOT/container-test-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
Ai-semble v2 Container Test Report
Generated: $(date)
Host: $(hostname)
Container Runtime: ${CONTAINER_CMD:-none}

=== Test Results ===
Total Tests: $total_tests
Passed: $passed_tests
Failed: $failed_tests
Success Rate: $(( passed_tests * 100 / total_tests ))%

=== Test Log ===
EOF
    
    cat "$LOG_FILE" >> "$report_file"
    
    log_success "Test report generated: $report_file"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Container testing script for Ai-semble v2

Options:
    --build-only        Only test container builds
    --config-only       Only test configurations
    --security-only     Only test security compliance
    --cleanup           Clean up test artifacts and exit
    --report            Generate detailed report
    -h, --help          Show this help message

Examples:
    $0                  # Run all tests
    $0 --build-only     # Test only container builds
    $0 --cleanup        # Clean up test artifacts
EOF
}

# Main execution function
main() {
    local build_only=false
    local config_only=false
    local security_only=false
    local cleanup_only=false
    local generate_report_flag=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                build_only=true
                shift
                ;;
            --config-only)
                config_only=true
                shift
                ;;
            --security-only)
                security_only=true
                shift
                ;;
            --cleanup)
                cleanup_only=true
                shift
                ;;
            --report)
                generate_report_flag=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Initialize log
    log_info "Ai-semble v2 Container Testing Started"
    log_info "Log file: $LOG_FILE"
    
    # Cleanup and exit if requested
    if [[ "$cleanup_only" == true ]]; then
        cleanup
        exit 0
    fi
    
    # Check container runtime
    check_container_runtime
    
    # Run tests based on options
    if [[ "$build_only" == true ]]; then
        test_all_containers
    elif [[ "$config_only" == true ]]; then
        test_pod_configuration
        test_quadlet_configuration
    elif [[ "$security_only" == true ]]; then
        test_security_compliance
    else
        # Run all tests
        test_all_containers
        test_pod_configuration
        test_quadlet_configuration
        test_security_compliance
        test_network_configuration
    fi
    
    # Generate report if requested
    if [[ "$generate_report_flag" == true ]]; then
        generate_report
    fi
    
    # Final summary
    log_info "=== Final Test Summary ==="
    log_info "Total tests: $total_tests"
    log_success "Passed: $passed_tests"
    
    if [[ $failed_tests -gt 0 ]]; then
        log_error "Failed: $failed_tests"
        log_info "Check $LOG_FILE for detailed error information"
        exit 1
    else
        log_success "All tests passed!"
        log_info "Ai-semble v2 containers are ready for deployment"
    fi
    
    # Cleanup
    cleanup
}

# Trap for cleanup on exit
trap cleanup EXIT

# Execute main function
main "$@"