#!/bin/bash
# Ai-semble v2 Performance Benchmark Suite
# Comprehensive performance testing and optimization

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-benchmark.log"
readonly RESULTS_DIR="$PROJECT_ROOT/benchmark_results"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Default configuration
DEFAULT_BASE_URL="http://localhost:8080"
DEFAULT_DURATION=300  # 5 minutes
DEFAULT_MAX_USERS=50

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

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Performance benchmark suite for Ai-semble v2

Options:
    --url URL           Base URL (default: $DEFAULT_BASE_URL)
    --duration SECONDS  Test duration in seconds (default: $DEFAULT_DURATION)
    --max-users NUM     Maximum concurrent users (default: $DEFAULT_MAX_USERS)
    --api-key KEY       API key for authentication
    --quick             Quick benchmark (reduced duration)
    --comprehensive     Comprehensive benchmark (extended tests)
    --baseline          Record baseline performance
    --compare FILE      Compare with baseline file
    --output-dir DIR    Output directory (default: $RESULTS_DIR)
    --no-charts         Skip chart generation
    -h, --help          Show this help message

Test Types:
    --health-only       Only health check tests
    --inference-only    Only AI inference tests
    --stress-only       Only stress tests
    --all               All test types (default)

Examples:
    $0                              # Basic benchmark
    $0 --quick                      # Quick 1-minute test
    $0 --comprehensive --duration 600  # 10-minute comprehensive test
    $0 --baseline                   # Record baseline performance
    $0 --compare baseline.json      # Compare with baseline
EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "=== Checking Prerequisites ==="
    
    # Check Python and required packages
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
    
    # Check if Ai-semble is running
    if ! curl -f -s "$BASE_URL/health" > /dev/null 2>&1; then
        log_warning "Ai-semble may not be running at $BASE_URL"
        log_info "Please ensure Ai-semble is running before benchmarking"
        return 1
    fi
    
    # Create results directory
    mkdir -p "$RESULTS_DIR"
    
    log_success "Prerequisites check passed"
}

# Install Python dependencies
install_dependencies() {
    log_info "=== Installing Python Dependencies ==="
    
    local requirements_content="aiohttp>=3.8.0
matplotlib>=3.5.0
psutil>=5.8.0
numpy>=1.21.0
asyncio-mqtt>=0.11.0"
    
    echo "$requirements_content" > "/tmp/benchmark_requirements.txt"
    
    if python3 -m pip install -q -r "/tmp/benchmark_requirements.txt"; then
        log_success "Dependencies installed"
    else
        log_error "Failed to install dependencies"
        return 1
    fi
}

# Run baseline performance test
run_baseline_test() {
    log_info "=== Running Baseline Performance Test ==="
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local baseline_file="$RESULTS_DIR/baseline_$timestamp.json"
    
    # Run standardized baseline test
    if python3 "$SCRIPT_DIR/load-test.py" \
        --url "$BASE_URL" \
        --test-type all \
        --users 10 \
        --duration 180 \
        --output "$baseline_file" \
        --charts; then
        
        log_success "Baseline test completed: $baseline_file"
        
        # Create symlink to latest baseline
        ln -sf "$(basename "$baseline_file")" "$RESULTS_DIR/baseline_latest.json"
        
        return 0
    else
        log_error "Baseline test failed"
        return 1
    fi
}

# Run quick benchmark
run_quick_benchmark() {
    log_info "=== Running Quick Benchmark ==="
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local results_file="$RESULTS_DIR/quick_benchmark_$timestamp.json"
    
    # Quick test: 1 minute, fewer users
    if python3 "$SCRIPT_DIR/load-test.py" \
        --url "$BASE_URL" \
        --test-type health \
        --users 5 \
        --duration 60 \
        --output "$results_file" \
        ${GENERATE_CHARTS:+--charts}; then
        
        log_success "Quick benchmark completed: $results_file"
        analyze_results "$results_file"
        return 0
    else
        log_error "Quick benchmark failed"
        return 1
    fi
}

# Run comprehensive benchmark
run_comprehensive_benchmark() {
    log_info "=== Running Comprehensive Benchmark ==="
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local results_dir="$RESULTS_DIR/comprehensive_$timestamp"
    
    mkdir -p "$results_dir"
    
    local tests=(
        "health:10:120"      # Health check: 10 users, 2 minutes
        "inference:5:180"    # AI inference: 5 users, 3 minutes
        "stress:20:300"      # Stress test: 20 users, 5 minutes
    )
    
    local all_results=()
    
    for test_spec in "${tests[@]}"; do
        local test_type="${test_spec%%:*}"
        local remaining="${test_spec#*:}"
        local users="${remaining%:*}"
        local duration="${remaining##*:}"
        
        log_info "Running $test_type test: $users users, ${duration}s"
        
        local test_results="$results_dir/${test_type}_results.json"
        
        if python3 "$SCRIPT_DIR/load-test.py" \
            --url "$BASE_URL" \
            --test-type "$test_type" \
            --users "$users" \
            --duration "$duration" \
            --output "$test_results" \
            ${GENERATE_CHARTS:+--charts}; then
            
            log_success "$test_type test completed"
            all_results+=("$test_results")
        else
            log_error "$test_type test failed"
        fi
        
        # Brief pause between tests
        sleep 10
    done
    
    # Generate comprehensive report
    if [[ ${#all_results[@]} -gt 0 ]]; then
        generate_comprehensive_report "$results_dir" "${all_results[@]}"
    fi
    
    log_success "Comprehensive benchmark completed: $results_dir"
}

# Run stress test
run_stress_test() {
    log_info "=== Running Stress Test ==="
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local results_file="$RESULTS_DIR/stress_test_$timestamp.json"
    
    # Stress test: gradual ramp-up
    if python3 "$SCRIPT_DIR/load-test.py" \
        --url "$BASE_URL" \
        --test-type stress \
        --users "$MAX_USERS" \
        --duration "$DURATION" \
        --output "$results_file" \
        ${GENERATE_CHARTS:+--charts}; then
        
        log_success "Stress test completed: $results_file"
        analyze_results "$results_file"
        return 0
    else
        log_error "Stress test failed"
        return 1
    fi
}

# Analyze benchmark results
analyze_results() {
    local results_file="$1"
    
    if [[ ! -f "$results_file" ]]; then
        log_error "Results file not found: $results_file"
        return 1
    fi
    
    log_info "=== Analyzing Results ==="
    
    # Extract key metrics using Python
    python3 << EOF
import json
import sys

try:
    with open('$results_file', 'r') as f:
        data = json.load(f)
    
    summary = data.get('performance_summary', {})
    
    print("\\n📊 PERFORMANCE ANALYSIS")
    print("=" * 40)
    print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
    print(f"Avg Response Time: {summary.get('avg_response_time', 0)*1000:.1f}ms")
    print(f"95th Percentile: {summary.get('p95_response_time', 0)*1000:.1f}ms")
    print(f"Throughput: {summary.get('requests_per_second', 0):.1f} req/s")
    print(f"Error Rate: {summary.get('error_rate', 0):.1f}%")
    
    # Performance assessment
    success_rate = summary.get('success_rate', 0)
    avg_response = summary.get('avg_response_time', 0) * 1000
    
    print(f"\\n🎯 ASSESSMENT:")
    
    if success_rate >= 99 and avg_response < 500:
        print("✅ EXCELLENT - Production ready")
    elif success_rate >= 95 and avg_response < 1000:
        print("🟡 GOOD - Minor optimizations recommended")
    elif success_rate >= 90 and avg_response < 2000:
        print("🟠 FAIR - Performance improvements needed")
    else:
        print("🔴 POOR - Significant issues require attention")
    
    print("=" * 40)
    
except Exception as e:
    print(f"Error analyzing results: {e}")
    sys.exit(1)
EOF
}

# Compare with baseline
compare_with_baseline() {
    local current_results="$1"
    local baseline_file="$2"
    
    if [[ ! -f "$baseline_file" ]]; then
        log_error "Baseline file not found: $baseline_file"
        return 1
    fi
    
    log_info "=== Comparing with Baseline ==="
    
    python3 << EOF
import json
import sys

try:
    with open('$current_results', 'r') as f:
        current = json.load(f)
    
    with open('$baseline_file', 'r') as f:
        baseline = json.load(f)
    
    curr_summary = current.get('performance_summary', {})
    base_summary = baseline.get('performance_summary', {})
    
    print("\\n📈 PERFORMANCE COMPARISON")
    print("=" * 50)
    print(f"{'Metric':<20} {'Baseline':<12} {'Current':<12} {'Change':<10}")
    print("-" * 50)
    
    metrics = [
        ('Success Rate %', 'success_rate'),
        ('Avg Response (ms)', 'avg_response_time'),
        ('P95 Response (ms)', 'p95_response_time'),
        ('Throughput (rps)', 'requests_per_second'),
        ('Error Rate %', 'error_rate')
    ]
    
    for label, key in metrics:
        base_val = base_summary.get(key, 0)
        curr_val = curr_summary.get(key, 0)
        
        if key.endswith('_time'):
            base_val *= 1000  # Convert to ms
            curr_val *= 1000
        
        if base_val > 0:
            change = ((curr_val - base_val) / base_val) * 100
            change_str = f"{change:+.1f}%"
        else:
            change_str = "N/A"
        
        print(f"{label:<20} {base_val:<12.1f} {curr_val:<12.1f} {change_str:<10}")
    
    print("=" * 50)
    
except Exception as e:
    print(f"Error comparing results: {e}")
    sys.exit(1)
EOF
}

# Generate comprehensive report
generate_comprehensive_report() {
    local results_dir="$1"
    shift
    local result_files=("$@")
    
    log_info "=== Generating Comprehensive Report ==="
    
    local report_file="$results_dir/comprehensive_report.html"
    
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Ai-semble v2 Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; }
        .excellent { background: #d4edda; border-color: #c3e6cb; }
        .good { background: #fff3cd; border-color: #ffeaa7; }
        .poor { background: #f8d7da; border-color: #f5c6cb; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Ai-semble v2 Performance Report</h1>
        <p>Generated on $(date)</p>
    </div>
EOF
    
    # Add results for each test type
    for result_file in "${result_files[@]}"; do
        if [[ -f "$result_file" ]]; then
            local test_name=$(basename "$result_file" .json)
            echo "<div class='section'><h2>$test_name Test Results</h2>" >> "$report_file"
            
            # Extract and format results
            python3 << EOF >> "$report_file"
import json
with open('$result_file', 'r') as f:
    data = json.load(f)
summary = data.get('performance_summary', {})
print(f"<div class='metric'>Success Rate: {summary.get('success_rate', 0):.1f}%</div>")
print(f"<div class='metric'>Avg Response: {summary.get('avg_response_time', 0)*1000:.1f}ms</div>")
print(f"<div class='metric'>Throughput: {summary.get('requests_per_second', 0):.1f} req/s</div>")
EOF
            
            echo "</div>" >> "$report_file"
        fi
    done
    
    echo "</body></html>" >> "$report_file"
    
    log_success "Comprehensive report generated: $report_file"
}

# Monitor system resources during benchmark
monitor_system_resources() {
    local duration="$1"
    local output_file="$2"
    
    log_info "Monitoring system resources for ${duration}s"
    
    # Background monitoring
    (
        for ((i=0; i<duration; i++)); do
            echo "$(date '+%Y-%m-%d %H:%M:%S'),$(cat /proc/loadavg | cut -d' ' -f1),$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')" >> "$output_file"
            sleep 1
        done
    ) &
    
    local monitor_pid=$!
    echo $monitor_pid
}

# Main execution function
main() {
    local base_url="$DEFAULT_BASE_URL"
    local duration="$DEFAULT_DURATION"
    local max_users="$DEFAULT_MAX_USERS"
    local api_key=""
    local test_type="all"
    local quick=false
    local comprehensive=false
    local baseline=false
    local compare_file=""
    local output_dir="$RESULTS_DIR"
    local generate_charts=true
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url)
                base_url="$2"
                shift 2
                ;;
            --duration)
                duration="$2"
                shift 2
                ;;
            --max-users)
                max_users="$2"
                shift 2
                ;;
            --api-key)
                api_key="$2"
                shift 2
                ;;
            --quick)
                quick=true
                shift
                ;;
            --comprehensive)
                comprehensive=true
                shift
                ;;
            --baseline)
                baseline=true
                shift
                ;;
            --compare)
                compare_file="$2"
                shift 2
                ;;
            --output-dir)
                output_dir="$2"
                shift 2
                ;;
            --no-charts)
                generate_charts=false
                shift
                ;;
            --health-only)
                test_type="health"
                shift
                ;;
            --inference-only)
                test_type="inference"
                shift
                ;;
            --stress-only)
                test_type="stress"
                shift
                ;;
            --all)
                test_type="all"
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
    
    # Set global variables
    BASE_URL="$base_url"
    DURATION="$duration"
    MAX_USERS="$max_users"
    RESULTS_DIR="$output_dir"
    
    if [[ "$generate_charts" == "true" ]]; then
        GENERATE_CHARTS="--charts"
    else
        GENERATE_CHARTS=""
    fi
    
    # Initialize log
    log_info "Ai-semble v2 Performance Benchmark Suite Started"
    log_info "Base URL: $BASE_URL"
    log_info "Duration: ${DURATION}s"
    log_info "Max Users: $MAX_USERS"
    log_info "Results Directory: $RESULTS_DIR"
    log_info "Log file: $LOG_FILE"
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Install dependencies
    install_dependencies
    
    # Execute benchmark based on options
    if [[ "$baseline" == "true" ]]; then
        run_baseline_test
    elif [[ "$quick" == "true" ]]; then
        run_quick_benchmark
    elif [[ "$comprehensive" == "true" ]]; then
        run_comprehensive_benchmark
    elif [[ "$test_type" == "stress" ]]; then
        run_stress_test
    else
        # Default benchmark
        log_info "Running standard benchmark"
        
        local timestamp=$(date '+%Y%m%d_%H%M%S')
        local results_file="$RESULTS_DIR/benchmark_$timestamp.json"
        
        if python3 "$SCRIPT_DIR/load-test.py" \
            --url "$BASE_URL" \
            --test-type "$test_type" \
            --users "$max_users" \
            --duration "$duration" \
            --output "$results_file" \
            ${GENERATE_CHARTS:+--charts}; then
            
            log_success "Benchmark completed: $results_file"
            analyze_results "$results_file"
            
            # Compare with baseline if specified
            if [[ -n "$compare_file" ]]; then
                compare_with_baseline "$results_file" "$compare_file"
            fi
        else
            log_error "Benchmark failed"
            exit 1
        fi
    fi
    
    log_success "Performance benchmark suite completed"
}

# Trap for cleanup on exit
trap 'log_info "Benchmark suite terminated"' EXIT

# Execute main function
main "$@"