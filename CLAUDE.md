# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ai-semble v2 is a Podman-native AI orchestration platform designed to provide secure, isolated AI development environments. The project migrates from Docker to Podman/systemd with rootless execution as the default.

## Architecture

The system uses a Pod-based architecture with three main containers:
- **Orchestrator Container**: Main coordination service (port 8080)
- **AI Services Container**: LLM, vision, and NLP services with GPU support
- **Data Processor Container**: Data processing workflows

All containers share volumes for models and data, managed through Podman pods with systemd integration.

## Common Commands

### Setup and Build
```bash
# Initial setup (from scripts/setup.sh)
systemctl --user enable podman.socket
podman volume create ai-semble-data
podman volume create ai-semble-models
podman network create ai-semble

# Build all container images
for dir in containers/*; do
    podman build -t localhost/ai-semble/$(basename $dir):latest $dir
done

# Install Quadlet configurations
mkdir -p ~/.config/containers/systemd/
cp quadlets/* ~/.config/containers/systemd/
systemctl --user daemon-reload
```

### Deployment and Management
```bash
# Start the pod
systemctl --user start ai-semble.pod

# Check status
podman pod ps
podman ps --pod

# View logs
journalctl --user -u ai-semble.pod

# Stop the pod
systemctl --user stop ai-semble.pod
```

### Development
```bash
# Run development pod with hot reload
podman play kube pods/ai-semble-dev.yaml

# Access container for debugging
podman exec -it ai-semble-orchestrator /bin/bash

# Monitor resource usage
podman stats --no-stream
```

### Testing
```bash
# Unit tests in container
podman run --rm \
  -v ./tests:/tests:Z \
  localhost/ai-semble/orchestrator:test \
  pytest /tests

# Integration tests
podman play kube pods/ai-semble-test.yaml
./scripts/integration-test.sh
```

## Key Implementation Details

### Security Model
- Rootless execution with user namespaces
- SELinux policies for container isolation
- Seccomp profiles for syscall filtering
- Read-only filesystem for orchestrator container

### Resource Management
- GPU access via NVIDIA Container Toolkit with CDI
- Memory limits configured per service (LLM: 8Gi)
- Shared volumes with appropriate SELinux labels (`:Z`)

### Network Configuration
- Custom bridge network (10.88.0.0/24)
- Pod-internal communication
- External access on port 8080

## File Structure Pattern

Expected directory structure when implementing:
```
ai-semble-v2/
├── containers/          # Container definitions
│   ├── orchestrator/    # Main coordination service
│   ├── ai-services/     # AI service containers
│   └── data-processor/  # Data processing container
├── pods/               # Kubernetes-compatible Pod definitions
├── quadlets/           # Systemd Quadlet configurations
├── security/           # Security policies (SELinux, Seccomp)
└── scripts/           # Setup and deployment scripts
```

## Development Notes

- Use `podman play kube` for Kubernetes compatibility
- Always use `:Z` suffix for volume mounts to handle SELinux
- GPU containers require `nvidia.com/gpu` resource specification
- Development containers should mount source code for hot reload
- Use structured logging with service identification for debugging