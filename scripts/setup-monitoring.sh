#!/bin/bash
# Monitoring Stack Setup Script for Ai-semble v2
# Sets up Prometheus, Grafana, and AlertManager

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly MONITORING_DIR="$PROJECT_ROOT/configs/monitoring"
readonly LOG_FILE="/tmp/ai-semble-monitoring-setup.log"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

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

Monitoring stack setup for Ai-semble v2

Options:
    --start             Start monitoring stack
    --stop              Stop monitoring stack
    --restart           Restart monitoring stack
    --status            Show monitoring stack status
    --logs              Show monitoring logs
    --cleanup           Remove monitoring stack
    --install-only      Only install configurations
    -h, --help          Show this help message

Examples:
    $0 --start          # Start monitoring stack
    $0 --status         # Check status
    $0 --logs           # View logs
EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "=== Checking Prerequisites ==="
    
    # Check for container runtime
    if command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
        COMPOSE_CMD="docker-compose"
        log_success "Docker found"
    elif command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
        COMPOSE_CMD="podman-compose"
        log_success "Podman found"
    else
        log_error "No container runtime found (docker or podman required)"
        exit 1
    fi
    
    # Check for docker-compose/podman-compose
    if ! command -v "$COMPOSE_CMD" &> /dev/null; then
        log_error "$COMPOSE_CMD not found"
        exit 1
    fi
    
    # Check if monitoring directory exists
    if [[ ! -d "$MONITORING_DIR" ]]; then
        log_error "Monitoring configuration directory not found: $MONITORING_DIR"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Install monitoring configurations
install_monitoring() {
    log_info "=== Installing Monitoring Configurations ==="
    
    # Create monitoring directories
    mkdir -p "$MONITORING_DIR/data/prometheus"
    mkdir -p "$MONITORING_DIR/data/grafana"
    mkdir -p "$MONITORING_DIR/data/alertmanager"
    
    # Set proper permissions
    chmod 755 "$MONITORING_DIR/data"/*
    
    # Validate configuration files
    local config_files=(
        "prometheus.yml"
        "alert_rules.yml"
        "alertmanager.yml"
        "grafana-dashboard.json"
        "grafana-datasources.yml"
        "grafana-dashboards.yml"
        "docker-compose.monitoring.yml"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$MONITORING_DIR/$config_file" ]]; then
            log_success "Configuration found: $config_file"
        else
            log_error "Configuration missing: $config_file"
            return 1
        fi
    done
    
    log_success "Monitoring configurations installed"
}

# Start monitoring stack
start_monitoring() {
    log_info "=== Starting Monitoring Stack ==="
    
    cd "$MONITORING_DIR"
    
    # Start services
    if $COMPOSE_CMD -f docker-compose.monitoring.yml up -d; then
        log_success "Monitoring stack started"
        
        # Wait for services to be ready
        log_info "Waiting for services to be ready..."
        sleep 30
        
        # Check service health
        check_service_health
        
        # Show access information
        show_access_info
        
    else
        log_error "Failed to start monitoring stack"
        return 1
    fi
}

# Stop monitoring stack
stop_monitoring() {
    log_info "=== Stopping Monitoring Stack ==="
    
    cd "$MONITORING_DIR"
    
    if $COMPOSE_CMD -f docker-compose.monitoring.yml down; then
        log_success "Monitoring stack stopped"
    else
        log_error "Failed to stop monitoring stack"
        return 1
    fi
}

# Restart monitoring stack
restart_monitoring() {
    log_info "=== Restarting Monitoring Stack ==="
    
    stop_monitoring
    sleep 5
    start_monitoring
}

# Check service health
check_service_health() {
    log_info "=== Checking Service Health ==="
    
    local services=(
        "prometheus:9090:/api/v1/query?query=up"
        "grafana:3000:/api/health"
        "alertmanager:9093:/api/v1/status"
        "node-exporter:9100:/metrics"
    )
    
    for service_info in "${services[@]}"; do
        local service_name="${service_info%%:*}"
        local port_path="${service_info#*:}"
        local port="${port_path%%:*}"
        local path="${port_path#*:}"
        
        log_info "Checking $service_name..."
        
        if curl -f -s "http://localhost:$port$path" > /dev/null; then
            log_success "$service_name is healthy"
        else
            log_warning "$service_name health check failed"
        fi
    done
}

# Show monitoring stack status
show_status() {
    log_info "=== Monitoring Stack Status ==="
    
    cd "$MONITORING_DIR"
    
    # Show container status
    $COMPOSE_CMD -f docker-compose.monitoring.yml ps
    
    echo
    log_info "Service Health Checks:"
    check_service_health
}

# Show monitoring logs
show_logs() {
    log_info "=== Monitoring Stack Logs ==="
    
    cd "$MONITORING_DIR"
    
    local service="${1:-}"
    
    if [[ -n "$service" ]]; then
        $COMPOSE_CMD -f docker-compose.monitoring.yml logs -f "$service"
    else
        $COMPOSE_CMD -f docker-compose.monitoring.yml logs -f
    fi
}

# Cleanup monitoring stack
cleanup_monitoring() {
    log_info "=== Cleaning Up Monitoring Stack ==="
    
    cd "$MONITORING_DIR"
    
    # Stop and remove containers
    $COMPOSE_CMD -f docker-compose.monitoring.yml down -v
    
    # Remove data directories (optional)
    read -p "Remove all monitoring data? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$MONITORING_DIR/data"
        log_success "Monitoring data removed"
    fi
    
    log_success "Cleanup completed"
}

# Show access information
show_access_info() {
    log_info "=== Monitoring Stack Access Information ==="
    
    cat << EOF

📊 Grafana Dashboard:
   URL: http://localhost:3000
   Username: admin
   Password: aisemble_admin_2024

📈 Prometheus:
   URL: http://localhost:9090

🚨 AlertManager:
   URL: http://localhost:9093

📋 Node Exporter:
   URL: http://localhost:9100/metrics

📊 cAdvisor:
   URL: http://localhost:8080

🔧 Quick Commands:
   Status: $0 --status
   Logs: $0 --logs
   Stop: $0 --stop

EOF
}

# Configure monitoring integration
configure_integration() {
    log_info "=== Configuring Ai-semble Integration ==="
    
    # Update Ai-semble configuration to enable metrics
    local orchestrator_config="$PROJECT_ROOT/containers/orchestrator/src/config/settings.py"
    
    if [[ -f "$orchestrator_config" ]]; then
        # Add monitoring configuration if not present
        if ! grep -q "ENABLE_METRICS" "$orchestrator_config"; then
            cat >> "$orchestrator_config" << 'EOF'

# Monitoring Configuration
ENABLE_METRICS = True
METRICS_PORT = 9091
PROMETHEUS_MULTIPROC_DIR = "/tmp/prometheus_multiproc"
EOF
            log_success "Metrics enabled in orchestrator configuration"
        else
            log_info "Metrics already enabled in orchestrator"
        fi
    else
        log_warning "Orchestrator configuration not found"
    fi
    
    log_success "Integration configuration completed"
}

# Main execution function
main() {
    local action=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --start)
                action="start"
                shift
                ;;
            --stop)
                action="stop"
                shift
                ;;
            --restart)
                action="restart"
                shift
                ;;
            --status)
                action="status"
                shift
                ;;
            --logs)
                action="logs"
                shift
                ;;
            --cleanup)
                action="cleanup"
                shift
                ;;
            --install-only)
                action="install"
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
    
    # Default action if none specified
    if [[ -z "$action" ]]; then
        action="start"
    fi
    
    # Initialize log
    log_info "Ai-semble v2 Monitoring Setup Started"
    log_info "Action: $action"
    log_info "Log file: $LOG_FILE"
    
    # Check prerequisites
    check_prerequisites
    
    # Execute action
    case "$action" in
        "start")
            install_monitoring
            configure_integration
            start_monitoring
            ;;
        "stop")
            stop_monitoring
            ;;
        "restart")
            restart_monitoring
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "cleanup")
            cleanup_monitoring
            ;;
        "install")
            install_monitoring
            configure_integration
            log_success "Monitoring configurations installed (not started)"
            ;;
        *)
            log_error "Unknown action: $action"
            usage
            exit 1
            ;;
    esac
    
    log_info "Monitoring setup completed"
}

# Trap for cleanup on exit
trap 'log_info "Monitoring setup script terminated"' EXIT

# Execute main function
main "$@"