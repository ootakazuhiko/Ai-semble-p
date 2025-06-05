#!/usr/bin/env python3
"""
Ai-semble v2 Intrusion Detection System
Real-time security monitoring and threat detection
"""

import asyncio
import time
import json
import logging
import psutil
import os
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Optional
import structlog
from dataclasses import dataclass, asdict

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("intrusion_detection")

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: str
    severity: str
    source_ip: str
    user_id: Optional[str]
    timestamp: str
    details: Dict
    action_taken: str

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_connections: int
    active_processes: int
    timestamp: str

class SecurityConfig:
    """Security configuration and thresholds"""
    
    # Rate limiting
    MAX_FAILED_ATTEMPTS = 5
    FAILED_ATTEMPT_WINDOW = 600  # 10 minutes
    IP_BLOCK_DURATION = 3600  # 1 hour
    
    # Resource monitoring
    CPU_THRESHOLD_WARNING = 80
    CPU_THRESHOLD_CRITICAL = 95
    MEMORY_THRESHOLD_WARNING = 85
    MEMORY_THRESHOLD_CRITICAL = 95
    DISK_THRESHOLD_WARNING = 85
    DISK_THRESHOLD_CRITICAL = 95
    
    # Network monitoring
    MAX_CONNECTIONS_PER_IP = 50
    SUSPICIOUS_PORTS = [22, 23, 3389, 5900, 1433, 3306]
    
    # File monitoring
    CRITICAL_FILES = [
        "/app/config/settings.py",
        "/app/models/",
        "/app/secrets/",
        "/etc/passwd",
        "/etc/shadow"
    ]
    
    # Suspicious processes
    SUSPICIOUS_PROCESS_NAMES = [
        "nc", "netcat", "ncat", "curl", "wget", "telnet",
        "nmap", "masscan", "zmap", "sqlmap", "metasploit"
    ]
    
    # Allowed IPs (for production, maintain whitelist)
    ALLOWED_IPS = {
        "127.0.0.1",
        "::1",
        "10.88.0.0/24"  # Internal container network
    }

class IntrusionDetector:
    """Main intrusion detection system"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.failed_attempts: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Set[str] = set()
        self.ip_block_times: Dict[str, float] = {}
        self.file_hashes: Dict[str, str] = {}
        self.baseline_metrics: Optional[SystemMetrics] = None
        self.security_events: List[SecurityEvent] = []
        self.is_running = False
        
        # Initialize file baseline
        self._initialize_file_baseline()
    
    def _initialize_file_baseline(self):
        """Create baseline hashes for critical files"""
        for file_path in self.config.CRITICAL_FILES:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        self.file_hashes[file_path] = file_hash
                        logger.info("file_baseline_created", file=file_path, hash=file_hash[:16])
                except Exception as e:
                    logger.error("file_baseline_failed", file=file_path, error=str(e))
    
    def record_failed_attempt(self, ip_address: str, user_id: str = None):
        """Record failed authentication attempt"""
        current_time = time.time()
        self.failed_attempts[ip_address].append(current_time)
        
        # Clean old attempts
        while (self.failed_attempts[ip_address] and 
               current_time - self.failed_attempts[ip_address][0] > self.config.FAILED_ATTEMPT_WINDOW):
            self.failed_attempts[ip_address].popleft()
        
        attempt_count = len(self.failed_attempts[ip_address])
        
        # Log the attempt
        self._log_security_event(
            "failed_authentication",
            "medium",
            ip_address,
            user_id,
            {"attempt_count": attempt_count}
        )
        
        # Block IP if threshold exceeded
        if attempt_count >= self.config.MAX_FAILED_ATTEMPTS:
            self._block_ip(ip_address, "rate_limit_exceeded")
    
    def _block_ip(self, ip_address: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        self.ip_block_times[ip_address] = time.time()
        
        self._log_security_event(
            "ip_blocked",
            "high",
            ip_address,
            None,
            {"reason": reason, "block_duration": self.config.IP_BLOCK_DURATION}
        )
        
        # Execute blocking action (in production, integrate with firewall)
        self._execute_ip_block(ip_address)
    
    def _execute_ip_block(self, ip_address: str):
        """Execute IP blocking (placeholder for firewall integration)"""
        logger.warning("ip_block_executed", ip=ip_address)
        # In production, integrate with iptables/firewalld:
        # os.system(f"iptables -A INPUT -s {ip_address} -j DROP")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is currently blocked"""
        if ip_address not in self.blocked_ips:
            return False
        
        # Check if block has expired
        block_time = self.ip_block_times.get(ip_address, 0)
        if time.time() - block_time > self.config.IP_BLOCK_DURATION:
            self._unblock_ip(ip_address)
            return False
        
        return True
    
    def _unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        self.ip_block_times.pop(ip_address, None)
        
        self._log_security_event(
            "ip_unblocked",
            "info",
            ip_address,
            None,
            {"reason": "block_expired"}
        )
    
    def check_suspicious_processes(self) -> List[Dict]:
        """Detect suspicious running processes"""
        suspicious = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username']):
                try:
                    proc_name = proc.info['name'].lower()
                    cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                    
                    # Check for suspicious process names
                    if any(sus_proc in proc_name for sus_proc in self.config.SUSPICIOUS_PROCESS_NAMES):
                        suspicious.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline,
                            'user': proc.info['username'],
                            'reason': 'suspicious_process_name'
                        })
                    
                    # Check for suspicious command patterns
                    suspicious_patterns = [
                        'reverse_tcp', 'meterpreter', '/bin/sh', '/bin/bash -i',
                        'python -c', 'perl -e', 'ruby -e', 'nc -l'
                    ]
                    
                    if any(pattern in cmdline for pattern in suspicious_patterns):
                        suspicious.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline,
                            'user': proc.info['username'],
                            'reason': 'suspicious_command_pattern'
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error("process_check_failed", error=str(e))
        
        return suspicious
    
    def check_network_anomalies(self) -> Dict:
        """Monitor network connections for anomalies"""
        anomalies = {
            'suspicious_connections': [],
            'port_scan_detected': False,
            'connection_count_by_ip': defaultdict(int)
        }
        
        try:
            connections = psutil.net_connections(kind='inet')
            
            for conn in connections:
                if not conn.raddr:
                    continue
                
                remote_ip = conn.raddr.ip
                remote_port = conn.raddr.port
                
                # Count connections per IP
                anomalies['connection_count_by_ip'][remote_ip] += 1
                
                # Check for connections to suspicious ports
                if remote_port in self.config.SUSPICIOUS_PORTS:
                    anomalies['suspicious_connections'].append({
                        'remote_ip': remote_ip,
                        'remote_port': remote_port,
                        'local_port': conn.laddr.port if conn.laddr else None,
                        'status': conn.status,
                        'reason': 'suspicious_port'
                    })
                
                # Check for external connections (not in allowed IPs)
                if not self._is_ip_allowed(remote_ip):
                    anomalies['suspicious_connections'].append({
                        'remote_ip': remote_ip,
                        'remote_port': remote_port,
                        'local_port': conn.laddr.port if conn.laddr else None,
                        'status': conn.status,
                        'reason': 'external_connection'
                    })
            
            # Detect potential port scans
            for ip, count in anomalies['connection_count_by_ip'].items():
                if count > self.config.MAX_CONNECTIONS_PER_IP:
                    anomalies['port_scan_detected'] = True
                    self._log_security_event(
                        "potential_port_scan",
                        "high",
                        ip,
                        None,
                        {"connection_count": count}
                    )
                    
        except Exception as e:
            logger.error("network_check_failed", error=str(e))
        
        return anomalies
    
    def _is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is in allowed list"""
        # Simplified check - in production, implement proper CIDR matching
        return ip_address in self.config.ALLOWED_IPS or ip_address.startswith('10.88.0.')
    
    def check_file_integrity(self) -> List[Dict]:
        """Check integrity of critical files"""
        integrity_violations = []
        
        for file_path, expected_hash in self.file_hashes.items():
            if not os.path.exists(file_path):
                integrity_violations.append({
                    'file': file_path,
                    'issue': 'file_deleted',
                    'expected_hash': expected_hash
                })
                continue
            
            try:
                with open(file_path, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
                
                if current_hash != expected_hash:
                    integrity_violations.append({
                        'file': file_path,
                        'issue': 'file_modified',
                        'expected_hash': expected_hash,
                        'current_hash': current_hash
                    })
                    
                    # Update baseline hash
                    self.file_hashes[file_path] = current_hash
                    
            except Exception as e:
                integrity_violations.append({
                    'file': file_path,
                    'issue': 'check_failed',
                    'error': str(e)
                })
        
        return integrity_violations
    
    def get_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics"""
        try:
            # Get disk usage for root partition
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=disk_percent,
                network_connections=len(psutil.net_connections()),
                active_processes=len(psutil.pids()),
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error("metrics_collection_failed", error=str(e))
            return SystemMetrics(0, 0, 0, 0, 0, datetime.utcnow().isoformat())
    
    def analyze_system_metrics(self, metrics: SystemMetrics):
        """Analyze system metrics for anomalies"""
        
        # CPU usage alerts
        if metrics.cpu_percent >= self.config.CPU_THRESHOLD_CRITICAL:
            self._log_security_event(
                "resource_exhaustion",
                "critical",
                "localhost",
                None,
                {"resource": "cpu", "usage": metrics.cpu_percent, "threshold": self.config.CPU_THRESHOLD_CRITICAL}
            )
        elif metrics.cpu_percent >= self.config.CPU_THRESHOLD_WARNING:
            self._log_security_event(
                "resource_high_usage",
                "warning",
                "localhost",
                None,
                {"resource": "cpu", "usage": metrics.cpu_percent, "threshold": self.config.CPU_THRESHOLD_WARNING}
            )
        
        # Memory usage alerts
        if metrics.memory_percent >= self.config.MEMORY_THRESHOLD_CRITICAL:
            self._log_security_event(
                "resource_exhaustion",
                "critical",
                "localhost",
                None,
                {"resource": "memory", "usage": metrics.memory_percent, "threshold": self.config.MEMORY_THRESHOLD_CRITICAL}
            )
        elif metrics.memory_percent >= self.config.MEMORY_THRESHOLD_WARNING:
            self._log_security_event(
                "resource_high_usage",
                "warning",
                "localhost",
                None,
                {"resource": "memory", "usage": metrics.memory_percent, "threshold": self.config.MEMORY_THRESHOLD_WARNING}
            )
        
        # Disk usage alerts
        if metrics.disk_percent >= self.config.DISK_THRESHOLD_CRITICAL:
            self._log_security_event(
                "resource_exhaustion",
                "critical",
                "localhost",
                None,
                {"resource": "disk", "usage": metrics.disk_percent, "threshold": self.config.DISK_THRESHOLD_CRITICAL}
            )
        elif metrics.disk_percent >= self.config.DISK_THRESHOLD_WARNING:
            self._log_security_event(
                "resource_high_usage",
                "warning",
                "localhost",
                None,
                {"resource": "disk", "usage": metrics.disk_percent, "threshold": self.config.DISK_THRESHOLD_WARNING}
            )
    
    def _log_security_event(self, event_type: str, severity: str, source_ip: str, 
                           user_id: Optional[str], details: Dict, action_taken: str = "logged"):
        """Log a security event"""
        
        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            details=details,
            action_taken=action_taken
        )
        
        self.security_events.append(event)
        
        # Log to structured logger
        logger.bind(
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            details=details,
            action_taken=action_taken
        ).info("security_event_detected")
        
        # Keep only recent events in memory
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-500:]
    
    async def continuous_monitoring(self, interval: int = 30):
        """Main monitoring loop"""
        self.is_running = True
        logger.info("intrusion_detection_started", interval=interval)
        
        while self.is_running:
            try:
                # Collect system metrics
                metrics = self.get_system_metrics()
                self.analyze_system_metrics(metrics)
                
                # Check for suspicious processes
                suspicious_procs = self.check_suspicious_processes()
                if suspicious_procs:
                    self._log_security_event(
                        "suspicious_processes_detected",
                        "high",
                        "localhost",
                        None,
                        {"processes": suspicious_procs, "count": len(suspicious_procs)}
                    )
                
                # Monitor network anomalies
                network_anomalies = self.check_network_anomalies()
                if network_anomalies['suspicious_connections']:
                    self._log_security_event(
                        "suspicious_network_activity",
                        "medium",
                        "localhost",
                        None,
                        {"anomalies": network_anomalies}
                    )
                
                # Check file integrity
                integrity_violations = self.check_file_integrity()
                if integrity_violations:
                    self._log_security_event(
                        "file_integrity_violation",
                        "high",
                        "localhost",
                        None,
                        {"violations": integrity_violations, "count": len(integrity_violations)}
                    )
                
                # Clean up expired blocks
                self._cleanup_expired_blocks()
                
                # Wait for next check
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error("monitoring_error", error=str(e))
                await asyncio.sleep(interval)
    
    def _cleanup_expired_blocks(self):
        """Remove expired IP blocks"""
        current_time = time.time()
        expired_ips = []
        
        for ip, block_time in self.ip_block_times.items():
            if current_time - block_time > self.config.IP_BLOCK_DURATION:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            self._unblock_ip(ip)
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_running = False
        logger.info("intrusion_detection_stopped")
    
    def get_security_summary(self) -> Dict:
        """Get current security status summary"""
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event.timestamp) > datetime.utcnow() - timedelta(hours=24)
        ]
        
        return {
            "blocked_ips": list(self.blocked_ips),
            "recent_events_24h": len(recent_events),
            "critical_events_24h": len([e for e in recent_events if e.severity == "critical"]),
            "high_events_24h": len([e for e in recent_events if e.severity == "high"]),
            "monitoring_active": self.is_running,
            "last_check": datetime.utcnow().isoformat()
        }

# FastAPI Integration Example
class SecurityMiddleware:
    """FastAPI middleware for intrusion detection integration"""
    
    def __init__(self, detector: IntrusionDetector):
        self.detector = detector
    
    async def __call__(self, request, call_next):
        # Get client IP
        client_ip = request.client.host
        
        # Check if IP is blocked
        if self.detector.is_ip_blocked(client_ip):
            return {"error": "Access denied", "status_code": 403}
        
        # Process request
        response = await call_next(request)
        
        # Log failed authentication attempts
        if response.status_code == 401:
            user_id = getattr(request.state, 'user_id', None)
            self.detector.record_failed_attempt(client_ip, user_id)
        
        return response

# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ai-semble v2 Intrusion Detection System")
    parser.add_argument("--interval", type=int, default=30, help="Monitoring interval in seconds")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = IntrusionDetector()
    
    if args.test:
        # Run test checks
        print("Running security checks...")
        metrics = detector.get_system_metrics()
        print(f"System metrics: {asdict(metrics)}")
        
        suspicious_procs = detector.check_suspicious_processes()
        print(f"Suspicious processes: {len(suspicious_procs)}")
        
        network_anomalies = detector.check_network_anomalies()
        print(f"Network anomalies: {len(network_anomalies['suspicious_connections'])}")
        
        integrity_violations = detector.check_file_integrity()
        print(f"File integrity violations: {len(integrity_violations)}")
        
        summary = detector.get_security_summary()
        print(f"Security summary: {summary}")
    else:
        # Start continuous monitoring
        try:
            asyncio.run(detector.continuous_monitoring(args.interval))
        except KeyboardInterrupt:
            detector.stop_monitoring()
            print("Intrusion detection stopped.")