# Ai-semble v2 Troubleshooting Guide

## 🔧 Quick Diagnosis

### Immediate Health Check
```bash
# Check system status
curl -X GET http://localhost:8080/health

# Run built-in diagnostics
./scripts/diagnose.sh

# Check container status
podman pod ps
podman ps --pod
```

## 🚨 Common Issues & Solutions

### 1. Container Startup Issues

#### Problem: Pod fails to start
```
Error: failed to start pod: container init failed
```

**Solution:**
```bash
# Check pod logs
journalctl --user -u ai-semble.pod

# Verify volumes exist
podman volume ls | grep ai-semble

# Recreate volumes if missing
podman volume create ai-semble-data
podman volume create ai-semble-models

# Restart pod
systemctl --user restart ai-semble.pod
```

#### Problem: Permission denied errors
```
Error: OCI runtime error: container_linux.go permission denied
```

**Solution:**
```bash
# Check SELinux contexts
ls -Z /path/to/volumes

# Fix SELinux labels
sudo restorecon -R /path/to/volumes

# Or disable SELinux temporarily for testing
sudo setenforce 0
```

#### Problem: Port already in use
```
Error: address already in use
```

**Solution:**
```bash
# Find process using port
sudo netstat -tulpn | grep :8080

# Kill process or change port in pod configuration
sudo kill <PID>

# Or modify pod YAML to use different ports
```

### 2. AI Service Issues

#### Problem: Model loading failures
```
ERROR: Failed to load model 'gpt-3.5-turbo'
```

**Diagnostic Steps:**
```bash
# Check available models
curl -X GET http://localhost:8081/models

# Check model file permissions
ls -la /var/lib/ai-semble/models/

# Check disk space
df -h

# Check memory usage
free -h
```

**Solution:**
```bash
# Download missing models
./scripts/download-models.sh

# Fix permissions
sudo chown -R 1000:1000 /var/lib/ai-semble/models/
sudo chmod -R 755 /var/lib/ai-semble/models/

# Restart AI service
podman restart ai-semble-llm
```

#### Problem: GPU not detected
```
CUDA error: no CUDA-capable device is detected
```

**Solution:**
```bash
# Install NVIDIA Container Toolkit
sudo dnf install nvidia-container-toolkit

# Verify GPU access
nvidia-smi

# Check container runtime configuration
podman info | grep -i nvidia

# Add GPU support to container
podman run --device nvidia.com/gpu=all ...
```

#### Problem: Out of memory errors
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Solution:**
```bash
# Check GPU memory
nvidia-smi

# Reduce batch size in model configuration
# Edit configs/models.yaml
batch_size: 1
max_length: 1024

# Restart services
systemctl --user restart ai-semble.pod
```

### 3. Network & Connectivity Issues

#### Problem: Services can't communicate
```
ConnectionError: Failed to connect to ai-semble-llm:8081
```

**Diagnostic Steps:**
```bash
# Check network configuration
podman network ls
podman network inspect ai-semble

# Test internal connectivity
podman exec ai-semble-orchestrator ping ai-semble-llm

# Check firewall rules
sudo firewall-cmd --list-all
```

**Solution:**
```bash
# Recreate network
podman network rm ai-semble
podman network create ai-semble

# Update pod configuration with correct network
# Restart all services
systemctl --user restart ai-semble.pod
```

#### Problem: External API timeouts
```
Timeout: Request to external API timed out
```

**Solution:**
```bash
# Check internet connectivity
curl -I https://api.openai.com

# Verify proxy settings (if applicable)
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Increase timeout values in configuration
# Edit containers/orchestrator/src/config/settings.py
REQUEST_TIMEOUT = 60
```

### 4. Performance Issues

#### Problem: Slow response times
```
Average response time: 30s (expected: <5s)
```

**Diagnostic Steps:**
```bash
# Check system resources
top
htop
iotop

# Monitor container resources
podman stats

# Check for bottlenecks
./scripts/performance_monitor.py
```

**Solution:**
```bash
# Scale up resources
# Edit pod configuration:
resources:
  limits:
    cpu: "8"
    memory: "16Gi"

# Enable GPU acceleration
# Add to container spec:
devices:
  - nvidia.com/gpu=all

# Optimize model parameters
# Reduce max_tokens, use smaller models for faster inference
```

#### Problem: High memory usage
```
Memory usage: 95% (critical threshold)
```

**Solution:**
```bash
# Identify memory-hungry processes
ps aux --sort=-%mem | head

# Clear model cache
curl -X POST http://localhost:8081/models/clear-cache

# Adjust memory limits
# Edit pod resources configuration

# Enable memory monitoring alerts
./scripts/operations_dashboard.py --mode monitor
```

### 5. Security & Authentication Issues

#### Problem: Authentication failures
```
401 Unauthorized: Invalid or expired token
```

**Solution:**
```bash
# Check token expiration
jwt-cli decode <your_token>

# Regenerate token
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'

# Verify user permissions
curl -X GET http://localhost:8080/auth/me \
  -H "Authorization: Bearer <token>"
```

#### Problem: SSL/TLS certificate errors
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
```bash
# Check certificate validity
openssl x509 -in /path/to/cert.pem -text -noout

# Update certificates
sudo dnf update ca-certificates

# For development, disable SSL verification (NOT for production)
export PYTHONHTTPSVERIFY=0
```

### 6. Data & Storage Issues

#### Problem: Disk space exhaustion
```
Error: No space left on device
```

**Solution:**
```bash
# Check disk usage
df -h
du -sh /var/lib/containers/*

# Clean up old containers and images
podman system prune -a

# Clear logs
sudo journalctl --vacuum-time=7d

# Move data to larger volume
# Update volume mounts in pod configuration
```

#### Problem: Database connection errors
```
OperationalError: could not connect to server
```

**Solution:**
```bash
# Check database service status
systemctl status postgresql

# Verify connection parameters
# Edit database configuration

# Test connection manually
psql -h localhost -U aisemble -d aisemble_db

# Restart database service
sudo systemctl restart postgresql
```

## 🔍 Advanced Debugging

### Enable Debug Logging
```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export PYTHONPATH=/app/src

# Or edit configuration
# containers/orchestrator/src/config/settings.py
LOG_LEVEL = "DEBUG"
```

### Container Debugging
```bash
# Access container shell
podman exec -it ai-semble-orchestrator /bin/bash

# Check container logs
podman logs ai-semble-orchestrator --tail 100

# Inspect container configuration
podman inspect ai-semble-orchestrator
```

### Network Debugging
```bash
# Test port connectivity
telnet localhost 8080

# Trace network traffic
sudo tcpdump -i any port 8080

# Check routing
ip route show
```

### Performance Profiling
```bash
# CPU profiling
sudo perf record -g -p <pid>
sudo perf report

# Memory profiling
valgrind --tool=memcheck --leak-check=full <command>

# Application profiling
python -m cProfile -o profile.stats your_script.py
```

## 🚨 Emergency Procedures

### Complete System Recovery
```bash
# 1. Stop all services
systemctl --user stop ai-semble.pod

# 2. Backup critical data
tar -czf backup-$(date +%Y%m%d).tar.gz \
  /var/lib/ai-semble/ \
  ~/.config/containers/

# 3. Reset containers
podman system reset --force

# 4. Reinstall from backup
./scripts/setup.sh
```

### Rollback to Previous Version
```bash
# 1. Check available tags
git tag -l

# 2. Checkout previous version
git checkout v1.9.0

# 3. Rebuild containers
./scripts/deploy.sh build

# 4. Update configuration if needed
```

### Security Incident Response
```bash
# 1. Isolate affected services
systemctl --user stop ai-semble.pod

# 2. Collect evidence
./scripts/collect-logs.sh
./security/intrusion-detection.py --test

# 3. Reset credentials
./scripts/reset-secrets.sh

# 4. Apply security patches
./security/security-hardening.sh --apply-all
```

## 📊 Monitoring & Alerting

### Set Up Monitoring
```bash
# Start monitoring dashboard
./scripts/operations_dashboard.py --mode dashboard

# Enable Prometheus metrics
# Add to configuration:
ENABLE_METRICS = True
METRICS_PORT = 9090

# Set up alerts
./scripts/setup-alerts.sh
```

### Health Check Automation
```bash
# Create health check script
#!/bin/bash
if ! curl -f http://localhost:8080/health; then
    systemctl --user restart ai-semble.pod
    echo "System restarted at $(date)" >> /var/log/ai-semble-recovery.log
fi

# Add to crontab
crontab -e
*/5 * * * * /path/to/health-check.sh
```

## 🔗 Getting Help

### Collect Diagnostic Information
```bash
# Run comprehensive diagnostics
./scripts/diagnose.sh --full > diagnostic-report.txt

# Include system information
uname -a >> diagnostic-report.txt
podman version >> diagnostic-report.txt
journalctl --user -u ai-semble.pod --since "1 hour ago" >> diagnostic-report.txt
```

### Contact Support
When contacting support, include:

1. **Error messages** (exact text)
2. **System information** (OS, Podman version)
3. **Configuration files** (sanitized)
4. **Log files** (relevant sections)
5. **Steps to reproduce** the issue

### Community Resources
- **GitHub Issues**: https://github.com/aisemble/aisemble-v2/issues
- **Discussion Forum**: https://community.aisemble.ai
- **Stack Overflow**: Tag questions with `aisemble`
- **Documentation**: https://docs.aisemble.ai

---

## 📝 Prevention Tips

### Regular Maintenance
```bash
# Weekly maintenance script
#!/bin/bash
# Update system packages
sudo dnf update

# Clean up containers
podman system prune

# Check disk space
df -h

# Verify backups
./scripts/verify-backups.sh

# Update security patches
./security/security-hardening.sh --check-only
```

### Monitoring Checklist
- [ ] Set up automated health checks
- [ ] Configure log rotation
- [ ] Monitor disk space
- [ ] Track memory usage
- [ ] Set up security alerts
- [ ] Regular backup verification
- [ ] Performance baseline monitoring

Remember: **Prevention is better than cure!** Regular monitoring and maintenance can prevent most issues before they become problems.