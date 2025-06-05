# Ai-semble v2 Security Policy

## 🔒 Security Overview

This document outlines the comprehensive security measures implemented in Ai-semble v2 to ensure secure AI orchestration in production environments.

## 🛡️ Container Security

### Rootless Execution
- All containers run as non-root users
- User namespaces enabled for isolation
- Reduced attack surface through privilege separation

### Image Security
```dockerfile
# Example security hardening in Containerfile
USER 1000:1000
COPY --chown=1000:1000 src/ /app/src/
RUN chmod -R 755 /app && \
    find /app -type f -name "*.py" -exec chmod 644 {} \;
```

### Resource Limits
```yaml
# Pod resource constraints
resources:
  limits:
    memory: "8Gi"
    cpu: "4"
  requests:
    memory: "2Gi" 
    cpu: "1"
```

## 🔐 Network Security

### Network Isolation
- Custom bridge network (10.88.0.0/24)
- Inter-container communication only
- No direct external access except orchestrator

### TLS Configuration
```yaml
# Example TLS setup for production
tls:
  enabled: true
  certFile: "/etc/certs/tls.crt"
  keyFile: "/etc/certs/tls.key"
  caFile: "/etc/certs/ca.crt"
```

### Firewall Rules
```bash
# Restrict external access
firewall-cmd --zone=public --add-port=8080/tcp --permanent
firewall-cmd --zone=public --remove-service=ssh --permanent
firewall-cmd --reload
```

## 🔍 Access Control

### Authentication
- JWT token-based authentication
- Token expiration: 24 hours
- Refresh token rotation

### Authorization
- Role-based access control (RBAC)
- API endpoint permissions
- Resource-level access control

### Example RBAC Configuration
```python
# Security roles definition
SECURITY_ROLES = {
    "admin": {
        "permissions": ["*"],
        "endpoints": ["*"]
    },
    "operator": {
        "permissions": ["read", "execute"],
        "endpoints": ["/health", "/ai/*", "/jobs/*"]
    },
    "viewer": {
        "permissions": ["read"],
        "endpoints": ["/health", "/status"]
    }
}
```

## 🛡️ Data Protection

### Encryption at Rest
- Model files encrypted with AES-256
- Configuration secrets encrypted
- Database encryption enabled

### Encryption in Transit
- All API communications over HTTPS
- Internal service mesh with mTLS
- Encrypted model downloads

### Secrets Management
```python
# Secure secrets handling
import os
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self.key = os.environ.get('ENCRYPTION_KEY')
        self.cipher = Fernet(self.key.encode()) if self.key else None
    
    def decrypt_secret(self, encrypted_value: str) -> str:
        if self.cipher:
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        return encrypted_value
```

## 🔒 SELinux Configuration

### Custom SELinux Policy
```selinux
# ai_semble.te - Custom SELinux policy
policy_module(ai_semble, 1.0)

require {
    type container_t;
    type container_file_t;
    class file { read write execute };
    class process { transition };
}

# Allow AI model file access
allow container_t container_file_t:file { read write };

# Restrict network access
allow container_t self:tcp_socket { create bind listen accept };
dontaudit container_t self:tcp_socket { connect };
```

### File Contexts
```selinux
# ai_semble.fc - File contexts
/opt/ai-semble/models(/.*)?    gen_context(system_u:object_r:container_file_t,s0)
/opt/ai-semble/data(/.*)?      gen_context(system_u:object_r:container_file_t,s0)
/opt/ai-semble/logs(/.*)?      gen_context(system_u:object_r:container_file_t,s0)
```

## 🔍 Seccomp Filtering

### System Call Restrictions
```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    {
      "names": ["read", "write", "open", "close", "mmap", "munmap"],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "names": ["clone", "fork", "vfork"],
      "action": "SCMP_ACT_ERRNO"
    },
    {
      "names": ["ptrace", "process_vm_readv", "process_vm_writev"],
      "action": "SCMP_ACT_KILL"
    }
  ]
}
```

## 🔐 Input Validation

### API Input Sanitization
```python
from pydantic import BaseModel, validator
import re

class AIRequestModel(BaseModel):
    prompt: str
    model_name: str
    
    @validator('prompt')
    def validate_prompt(cls, v):
        # Remove potential injection attempts
        if re.search(r'[<>\"\'&]', v):
            raise ValueError('Invalid characters in prompt')
        if len(v) > 10000:
            raise ValueError('Prompt too long')
        return v.strip()
    
    @validator('model_name')
    def validate_model_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid model name format')
        return v
```

### File Upload Security
```python
import magic
from pathlib import Path

ALLOWED_EXTENSIONS = {'.txt', '.json', '.csv', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def validate_upload(file_path: Path) -> bool:
    # Check file extension
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    
    # Check file size
    if file_path.stat().st_size > MAX_FILE_SIZE:
        return False
    
    # Check MIME type
    mime_type = magic.from_file(str(file_path), mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        return False
    
    return True
```

## 🔍 Logging & Auditing

### Security Event Logging
```python
import structlog
from datetime import datetime

security_logger = structlog.get_logger("security")

def log_security_event(event_type: str, user_id: str, details: dict):
    security_logger.info(
        "security_event",
        event_type=event_type,
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        details=details,
        severity="high" if event_type in ["unauthorized_access", "injection_attempt"] else "medium"
    )
```

### Audit Trail
- All API requests logged with user context
- Model access and modifications tracked
- Configuration changes audited
- Failed authentication attempts monitored

## 🛡️ Runtime Security

### Health Checks with Security Context
```python
from fastapi import HTTPException
import psutil
import os

async def security_health_check():
    """Enhanced health check with security validations"""
    
    # Check for suspicious processes
    suspicious_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if any(suspect in str(proc.info['cmdline']).lower() 
               for suspect in ['nc', 'netcat', 'curl', 'wget']):
            suspicious_processes.append(proc.info)
    
    # Check file permissions
    critical_files = ['/app/config', '/app/models', '/app/secrets']
    for file_path in critical_files:
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            if stat.st_mode & 0o077:  # Check for world/group permissions
                raise HTTPException(status_code=500, detail="Insecure file permissions detected")
    
    return {
        "status": "healthy",
        "security_checks": "passed",
        "suspicious_processes": suspicious_processes
    }
```

### Intrusion Detection
```python
import time
from collections import defaultdict, deque

class IntrusionDetector:
    def __init__(self):
        self.failed_attempts = defaultdict(deque)
        self.blocked_ips = set()
        
    def record_failed_attempt(self, ip_address: str):
        current_time = time.time()
        self.failed_attempts[ip_address].append(current_time)
        
        # Remove old attempts (older than 10 minutes)
        while (self.failed_attempts[ip_address] and 
               current_time - self.failed_attempts[ip_address][0] > 600):
            self.failed_attempts[ip_address].popleft()
        
        # Block IP if too many failed attempts
        if len(self.failed_attempts[ip_address]) >= 5:
            self.blocked_ips.add(ip_address)
            log_security_event("ip_blocked", "system", {"ip": ip_address})
    
    def is_blocked(self, ip_address: str) -> bool:
        return ip_address in self.blocked_ips
```

## 🔒 Model Security

### Model Integrity Verification
```python
import hashlib
import json

def verify_model_integrity(model_path: str, expected_hash: str) -> bool:
    """Verify model file hasn't been tampered with"""
    with open(model_path, 'rb') as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    return actual_hash == expected_hash

def secure_model_loading(model_name: str):
    """Load model with security checks"""
    model_config = load_model_config(model_name)
    
    # Verify model integrity
    if not verify_model_integrity(model_config['path'], model_config['hash']):
        raise SecurityError(f"Model integrity check failed for {model_name}")
    
    # Check model permissions
    if not check_model_permissions(model_name, current_user):
        raise SecurityError(f"Insufficient permissions to access {model_name}")
    
    return load_model(model_config['path'])
```

## 🔍 Security Monitoring

### Real-time Threat Detection
```python
async def monitor_security_threats():
    """Continuous security monitoring"""
    while True:
        # Monitor CPU/Memory usage for anomalies
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        
        if cpu_usage > 90 or memory_usage > 95:
            log_security_event("resource_anomaly", "system", {
                "cpu": cpu_usage,
                "memory": memory_usage
            })
        
        # Monitor network connections
        connections = psutil.net_connections()
        suspicious_connections = [
            conn for conn in connections 
            if conn.status == 'ESTABLISHED' and 
            conn.raddr and conn.raddr.ip not in ALLOWED_IPS
        ]
        
        if suspicious_connections:
            log_security_event("suspicious_network_activity", "system", {
                "connections": len(suspicious_connections)
            })
        
        await asyncio.sleep(30)
```

## 📋 Security Checklist

### Pre-deployment Security Validation
- [ ] All dependencies updated to latest secure versions
- [ ] SELinux policies applied and tested
- [ ] Seccomp profiles configured
- [ ] Network isolation verified
- [ ] Access controls tested
- [ ] Encryption keys rotated
- [ ] Security logging enabled
- [ ] Intrusion detection active
- [ ] Backup and recovery procedures tested
- [ ] Incident response plan documented

### Regular Security Maintenance
- [ ] Weekly dependency vulnerability scans
- [ ] Monthly security policy reviews
- [ ] Quarterly penetration testing
- [ ] Annual security architecture assessment

## 🚨 Incident Response

### Security Incident Classification
1. **Critical**: Data breach, system compromise
2. **High**: Unauthorized access, service disruption
3. **Medium**: Failed authentication, suspicious activity
4. **Low**: Policy violations, configuration drift

### Response Procedures
1. **Detection**: Automated alerts and manual monitoring
2. **Assessment**: Severity classification and impact analysis
3. **Containment**: Isolate affected systems
4. **Eradication**: Remove threat and vulnerabilities
5. **Recovery**: Restore services with enhanced security
6. **Lessons Learned**: Update policies and procedures

This security policy provides comprehensive protection for Ai-semble v2 in production environments while maintaining operational efficiency.