#!/bin/bash
# Ai-semble v2 Security Hardening Script
# Implements additional security measures for production deployment

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="/tmp/ai-semble-security-hardening.log"

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

Security hardening script for Ai-semble v2

Options:
    --check-only        Only check current security status
    --apply-all         Apply all security hardening measures
    --selinux           Configure SELinux policies
    --firewall          Configure firewall rules
    --file-permissions  Set secure file permissions
    --monitoring        Setup security monitoring
    --backup            Create security configuration backup
    -h, --help          Show this help message

Examples:
    $0 --check-only                # Check current security status
    $0 --apply-all                 # Apply all security measures
    $0 --selinux --firewall        # Apply specific measures
EOF
}

# Check if running as root
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root - some operations will be skipped for security"
        return 0
    fi
    log_info "Running as non-root user"
    return 1
}

# Check current security status
check_security_status() {
    log_info "=== Security Status Check ==="
    
    local issues=0
    
    # Check SELinux status
    if command -v getenforce &> /dev/null; then
        local selinux_status=$(getenforce 2>/dev/null || echo "Disabled")
        if [[ "$selinux_status" == "Enforcing" ]]; then
            log_success "SELinux: Enforcing"
        else
            log_warning "SELinux: $selinux_status (should be Enforcing)"
            ((issues++))
        fi
    else
        log_warning "SELinux: Not available"
        ((issues++))
    fi
    
    # Check firewall status
    if command -v firewall-cmd &> /dev/null; then
        if systemctl is-active --quiet firewalld; then
            log_success "Firewall: Active"
        else
            log_warning "Firewall: Inactive"
            ((issues++))
        fi
    elif command -v ufw &> /dev/null; then
        if ufw status | grep -q "Status: active"; then
            log_success "UFW Firewall: Active"
        else
            log_warning "UFW Firewall: Inactive"
            ((issues++))
        fi
    else
        log_warning "No firewall detected"
        ((issues++))
    fi
    
    # Check file permissions
    local critical_files=(
        "$PROJECT_ROOT/security/seccomp/ai-semble.json"
        "$PROJECT_ROOT/security/selinux/ai_semble.te"
        "$PROJECT_ROOT/scripts/setup.sh"
        "$PROJECT_ROOT/scripts/deploy.sh"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ -f "$file" ]]; then
            local perms=$(stat -c "%a" "$file")
            if [[ "$perms" =~ ^[67][0-4][0-4]$ ]]; then
                log_success "File permissions OK: $file ($perms)"
            else
                log_warning "Insecure file permissions: $file ($perms)"
                ((issues++))
            fi
        fi
    done
    
    # Check for password files
    local password_files=(
        "$PROJECT_ROOT/.env"
        "$PROJECT_ROOT/secrets.txt"
        "$PROJECT_ROOT/config/passwords"
    )
    
    for file in "${password_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_warning "Potential password file found: $file"
            ((issues++))
        fi
    done
    
    # Check container security
    if command -v podman &> /dev/null; then
        log_info "Checking Podman security configuration..."
        
        # Check if rootless
        if podman info --format="{{.Host.Security.Rootless}}" 2>/dev/null | grep -q "true"; then
            log_success "Podman: Running rootless"
        else
            log_warning "Podman: Not running rootless"
            ((issues++))
        fi
        
        # Check for privileged containers
        local privileged_containers=$(podman ps --format="{{.Names}} {{.Ports}}" | grep -c ":privileged" || echo "0")
        if [[ "$privileged_containers" -eq 0 ]]; then
            log_success "No privileged containers detected"
        else
            log_warning "Privileged containers detected: $privileged_containers"
            ((issues++))
        fi
    fi
    
    # Summary
    log_info "=== Security Check Summary ==="
    if [[ $issues -eq 0 ]]; then
        log_success "No security issues detected"
        return 0
    else
        log_warning "$issues security issues found"
        return 1
    fi
}

# Configure SELinux policies
configure_selinux() {
    log_info "=== Configuring SELinux ==="
    
    if ! command -v getenforce &> /dev/null; then
        log_warning "SELinux not available on this system"
        return 1
    fi
    
    local selinux_status=$(getenforce)
    log_info "Current SELinux status: $selinux_status"
    
    # Install SELinux policy if it exists
    local policy_file="$PROJECT_ROOT/security/selinux/ai_semble.te"
    if [[ -f "$policy_file" ]]; then
        log_info "Installing custom SELinux policy..."
        
        # Compile and install policy (requires root)
        if check_privileges; then
            log_warning "Skipping SELinux policy installation (requires root privileges)"
        else
            log_info "Compiling SELinux policy..."
            if checkmodule -M -m -o "/tmp/ai_semble.mod" "$policy_file" 2>/dev/null; then
                semodule_package -o "/tmp/ai_semble.pp" -m "/tmp/ai_semble.mod"
                sudo semodule -i "/tmp/ai_semble.pp"
                log_success "SELinux policy installed"
                
                # Clean up
                rm -f "/tmp/ai_semble.mod" "/tmp/ai_semble.pp"
            else
                log_error "Failed to compile SELinux policy"
                return 1
            fi
        fi
    fi
    
    # Set file contexts
    local fc_file="$PROJECT_ROOT/security/selinux/ai_semble.fc"
    if [[ -f "$fc_file" ]] && check_privileges; then
        log_info "Setting SELinux file contexts..."
        sudo setsebool -P container_use_cephfs on
        sudo setsebool -P virt_use_fusefs on
        log_success "SELinux contexts configured"
    fi
    
    # Verify SELinux is enforcing
    if [[ "$selinux_status" != "Enforcing" ]]; then
        log_warning "SELinux is not in enforcing mode"
        log_info "To enable: sudo setenforce 1"
        log_info "To make permanent: edit /etc/selinux/config"
    else
        log_success "SELinux is properly enforcing"
    fi
}

# Configure firewall rules
configure_firewall() {
    log_info "=== Configuring Firewall ==="
    
    if command -v firewall-cmd &> /dev/null; then
        configure_firewalld
    elif command -v ufw &> /dev/null; then
        configure_ufw
    else
        log_warning "No supported firewall found"
        return 1
    fi
}

configure_firewalld() {
    log_info "Configuring firewalld..."
    
    if ! systemctl is-active --quiet firewalld; then
        log_info "Starting firewalld..."
        if check_privileges; then
            sudo systemctl start firewalld
            sudo systemctl enable firewalld
        else
            log_warning "Cannot start firewalld without root privileges"
            return 1
        fi
    fi
    
    # Configure zones and rules
    if check_privileges; then
        # Allow only necessary ports
        sudo firewall-cmd --permanent --remove-service=ssh 2>/dev/null || true
        sudo firewall-cmd --permanent --remove-service=dhcpv6-client 2>/dev/null || true
        
        # Add Ai-semble services
        sudo firewall-cmd --permanent --add-port=8080/tcp  # Orchestrator
        sudo firewall-cmd --permanent --add-port=9090/tcp  # Prometheus (if enabled)
        sudo firewall-cmd --permanent --add-port=3000/tcp  # Grafana (if enabled)
        
        # Reload firewall
        sudo firewall-cmd --reload
        
        log_success "Firewalld configured"
    else
        log_warning "Cannot configure firewall without root privileges"
    fi
}

configure_ufw() {
    log_info "Configuring UFW..."
    
    if check_privileges; then
        # Reset to defaults
        echo "y" | sudo ufw --force reset
        
        # Default policies
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        
        # Allow necessary ports
        sudo ufw allow 8080/tcp comment "Ai-semble Orchestrator"
        sudo ufw allow 9090/tcp comment "Prometheus"
        sudo ufw allow 3000/tcp comment "Grafana"
        
        # Enable UFW
        echo "y" | sudo ufw --force enable
        
        log_success "UFW configured"
    else
        log_warning "Cannot configure UFW without root privileges"
    fi
}

# Set secure file permissions
set_file_permissions() {
    log_info "=== Setting Secure File Permissions ==="
    
    # Set directory permissions
    find "$PROJECT_ROOT" -type d -exec chmod 755 {} \;
    
    # Set file permissions
    find "$PROJECT_ROOT" -type f -exec chmod 644 {} \;
    
    # Set executable permissions for scripts
    local scripts=(
        "$PROJECT_ROOT/scripts/"*.sh
        "$PROJECT_ROOT/security/security-hardening.sh"
        "$PROJECT_ROOT/security/intrusion-detection.py"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            chmod 755 "$script"
            log_info "Set executable: $script"
        fi
    done
    
    # Secure sensitive files
    local sensitive_files=(
        "$PROJECT_ROOT/security/seccomp/ai-semble.json"
        "$PROJECT_ROOT/security/selinux/"*
        "$PROJECT_ROOT/quadlets/"*
    )
    
    for file in "${sensitive_files[@]}"; do
        if [[ -f "$file" ]]; then
            chmod 640 "$file"
            log_info "Secured sensitive file: $file"
        fi
    done
    
    # Remove world permissions from configuration
    find "$PROJECT_ROOT/configs" -type f -exec chmod 640 {} \; 2>/dev/null || true
    
    log_success "File permissions configured"
}

# Setup security monitoring
setup_monitoring() {
    log_info "=== Setting Up Security Monitoring ==="
    
    # Create monitoring directories
    local monitor_dirs=(
        "/var/log/ai-semble"
        "/var/lib/ai-semble/monitoring"
    )
    
    for dir in "${monitor_dirs[@]}"; do
        if check_privileges; then
            sudo mkdir -p "$dir"
            sudo chown "$(id -u):$(id -g)" "$dir"
            sudo chmod 750 "$dir"
            log_info "Created monitoring directory: $dir"
        else
            mkdir -p "$HOME/.ai-semble/$(basename "$dir")"
            log_info "Created user monitoring directory: $HOME/.ai-semble/$(basename "$dir")"
        fi
    done
    
    # Setup log rotation
    local logrotate_config="/etc/logrotate.d/ai-semble"
    if check_privileges; then
        cat > "/tmp/ai-semble-logrotate" << 'EOF'
/var/log/ai-semble/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 ai-semble ai-semble
    postrotate
        systemctl reload ai-semble-orchestrator || true
    endscript
}
EOF
        sudo mv "/tmp/ai-semble-logrotate" "$logrotate_config"
        log_success "Log rotation configured"
    else
        log_warning "Cannot configure system log rotation without root privileges"
    fi
    
    # Install intrusion detection script
    local ids_script="$PROJECT_ROOT/security/intrusion-detection.py"
    if [[ -f "$ids_script" ]]; then
        chmod +x "$ids_script"
        
        # Create systemd service for IDS
        if check_privileges; then
            cat > "/tmp/ai-semble-ids.service" << EOF
[Unit]
Description=Ai-semble Intrusion Detection System
After=network.target

[Service]
Type=simple
User=ai-semble
Group=ai-semble
ExecStart=/usr/bin/python3 $ids_script --interval 30
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
            sudo mv "/tmp/ai-semble-ids.service" "/etc/systemd/system/"
            sudo systemctl daemon-reload
            log_success "Intrusion detection service configured"
        else
            log_warning "Cannot install systemd service without root privileges"
        fi
    fi
    
    log_success "Security monitoring configured"
}

# Create security configuration backup
create_backup() {
    log_info "=== Creating Security Configuration Backup ==="
    
    local backup_dir="$PROJECT_ROOT/backups/security-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup security configurations
    local backup_items=(
        "$PROJECT_ROOT/security/"
        "$PROJECT_ROOT/quadlets/"
        "$PROJECT_ROOT/configs/"
        "/etc/systemd/system/ai-semble*" 2>/dev/null || true
    )
    
    for item in "${backup_items[@]}"; do
        if [[ -e "$item" ]]; then
            cp -r "$item" "$backup_dir/" 2>/dev/null || true
            log_info "Backed up: $item"
        fi
    done
    
    # Create backup manifest
    cat > "$backup_dir/manifest.txt" << EOF
Ai-semble v2 Security Configuration Backup
Created: $(date)
Host: $(hostname)
User: $(whoami)
Kernel: $(uname -r)

Files included:
$(find "$backup_dir" -type f | sort)
EOF
    
    # Compress backup
    tar -czf "$backup_dir.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    rm -rf "$backup_dir"
    
    log_success "Security backup created: $backup_dir.tar.gz"
}

# Install additional security tools
install_security_tools() {
    log_info "=== Installing Additional Security Tools ==="
    
    if check_privileges; then
        # Detect package manager
        if command -v dnf &> /dev/null; then
            sudo dnf install -y fail2ban aide rkhunter lynis
        elif command -v apt &> /dev/null; then
            sudo apt update
            sudo apt install -y fail2ban aide rkhunter lynis
        elif command -v yum &> /dev/null; then
            sudo yum install -y fail2ban aide rkhunter lynis
        else
            log_warning "No supported package manager found"
            return 1
        fi
        
        log_success "Security tools installed"
    else
        log_warning "Cannot install security tools without root privileges"
    fi
}

# Apply all security hardening measures
apply_all() {
    log_info "=== Applying All Security Hardening Measures ==="
    
    local failed=0
    
    create_backup || ((failed++))
    set_file_permissions || ((failed++))
    configure_selinux || ((failed++))
    configure_firewall || ((failed++))
    setup_monitoring || ((failed++))
    install_security_tools || ((failed++))
    
    if [[ $failed -eq 0 ]]; then
        log_success "All security hardening measures applied successfully"
        
        # Final security check
        log_info "Running final security verification..."
        if check_security_status; then
            log_success "Security hardening completed successfully"
        else
            log_warning "Some security issues remain - manual intervention may be required"
        fi
    else
        log_warning "$failed security measures failed - review logs for details"
        return 1
    fi
}

# Generate security report
generate_report() {
    log_info "=== Generating Security Report ==="
    
    local report_file="$PROJECT_ROOT/security-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
Ai-semble v2 Security Assessment Report
Generated: $(date)
Host: $(hostname)
Kernel: $(uname -r)

=== System Information ===
OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo "Unknown")
Architecture: $(uname -m)
Uptime: $(uptime)

=== Security Status ===
EOF
    
    # Append security check results
    check_security_status >> "$report_file" 2>&1
    
    log_success "Security report generated: $report_file"
}

# Main execution
main() {
    local check_only=false
    local apply_all_flag=false
    local selinux_flag=false
    local firewall_flag=false
    local file_perms_flag=false
    local monitoring_flag=false
    local backup_flag=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-only)
                check_only=true
                shift
                ;;
            --apply-all)
                apply_all_flag=true
                shift
                ;;
            --selinux)
                selinux_flag=true
                shift
                ;;
            --firewall)
                firewall_flag=true
                shift
                ;;
            --file-permissions)
                file_perms_flag=true
                shift
                ;;
            --monitoring)
                monitoring_flag=true
                shift
                ;;
            --backup)
                backup_flag=true
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
    log_info "Ai-semble v2 Security Hardening Script Started"
    log_info "Log file: $LOG_FILE"
    
    if [[ "$check_only" == true ]]; then
        check_security_status
        generate_report
    elif [[ "$apply_all_flag" == true ]]; then
        apply_all
    else
        # Apply individual measures
        [[ "$backup_flag" == true ]] && create_backup
        [[ "$file_perms_flag" == true ]] && set_file_permissions
        [[ "$selinux_flag" == true ]] && configure_selinux
        [[ "$firewall_flag" == true ]] && configure_firewall
        [[ "$monitoring_flag" == true ]] && setup_monitoring
        
        # If no specific flags, show usage
        if [[ "$backup_flag" == false && "$file_perms_flag" == false && 
              "$selinux_flag" == false && "$firewall_flag" == false && 
              "$monitoring_flag" == false ]]; then
            usage
            exit 1
        fi
    fi
    
    log_info "Security hardening script completed"
}

# Trap for cleanup
trap 'log_error "Script interrupted"' INT TERM

# Execute main function
main "$@"