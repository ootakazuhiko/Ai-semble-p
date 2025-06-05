# Ai-semble v2 API Reference

## 🎯 Overview

Ai-semble v2 provides a comprehensive REST API for AI orchestration, model management, and system operations. This reference documents all available endpoints, request/response formats, and integration examples.

## 🔗 Base URL

```
Production: https://your-domain.com/api/v2
Development: http://localhost:8080/api/v2
```

## 🔐 Authentication

All API requests require authentication using JWT tokens.

### Authentication Header
```http
Authorization: Bearer <jwt_token>
```

### Getting an Access Token
```http
POST /auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

## 🧠 AI Services API

### LLM (Large Language Model) Service

#### Generate Text
```http
POST /ai/llm/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "Explain quantum computing",
  "model": "gpt-3.5-turbo",
  "max_tokens": 500,
  "temperature": 0.7,
  "parameters": {
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  }
}
```

**Response:**
```json
{
  "request_id": "req_123456789",
  "model": "gpt-3.5-turbo",
  "generated_text": "Quantum computing is a revolutionary...",
  "metadata": {
    "tokens_used": 487,
    "processing_time": 1.234,
    "cost": 0.001234
  },
  "status": "completed"
}
```

#### List Available Models
```http
GET /ai/llm/models
Authorization: Bearer <token>
```

**Response:**
```json
{
  "models": [
    {
      "id": "gpt-3.5-turbo",
      "name": "GPT-3.5 Turbo",
      "description": "Fast, efficient language model",
      "max_tokens": 4096,
      "cost_per_token": 0.000002,
      "capabilities": ["text_generation", "chat", "completion"],
      "status": "available"
    },
    {
      "id": "claude-3-sonnet",
      "name": "Claude 3 Sonnet",
      "description": "Advanced reasoning and analysis",
      "max_tokens": 200000,
      "cost_per_token": 0.000003,
      "capabilities": ["text_generation", "analysis", "coding"],
      "status": "available"
    }
  ]
}
```

#### Chat Completion
```http
POST /ai/llm/chat
Content-Type: application/json
Authorization: Bearer <token>

{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful AI assistant."
    },
    {
      "role": "user", 
      "content": "What is the capital of France?"
    }
  ],
  "model": "gpt-3.5-turbo",
  "temperature": 0.7,
  "max_tokens": 150
}
```

**Response:**
```json
{
  "request_id": "req_987654321",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 23,
    "completion_tokens": 8,
    "total_tokens": 31
  }
}
```

### Vision Service

#### Analyze Image
```http
POST /ai/vision/analyze
Content-Type: multipart/form-data
Authorization: Bearer <token>

image: <binary_image_data>
analysis_type: ["object_detection", "text_extraction", "scene_analysis"]
model: "yolo-v8"
```

**Response:**
```json
{
  "request_id": "req_456789123",
  "image_info": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG",
    "size_bytes": 245760
  },
  "analysis_results": {
    "objects": [
      {
        "class": "person",
        "confidence": 0.95,
        "bbox": [100, 200, 300, 600],
        "attributes": {
          "gender": "unknown",
          "age_range": "adult"
        }
      },
      {
        "class": "car",
        "confidence": 0.87,
        "bbox": [500, 300, 800, 500]
      }
    ],
    "text": [
      {
        "text": "STOP",
        "confidence": 0.99,
        "bbox": [150, 50, 200, 100]
      }
    ],
    "scene": {
      "setting": "urban_street",
      "time_of_day": "daytime",
      "weather": "clear"
    }
  },
  "processing_time": 2.456
}
```

#### Image Classification
```http
POST /ai/vision/classify
Content-Type: multipart/form-data
Authorization: Bearer <token>

image: <binary_image_data>
model: "resnet-50"
top_k: 5
```

**Response:**
```json
{
  "request_id": "req_789123456",
  "predictions": [
    {
      "class": "golden_retriever",
      "confidence": 0.94,
      "class_id": 207
    },
    {
      "class": "labrador_retriever", 
      "confidence": 0.03,
      "class_id": 208
    },
    {
      "class": "nova_scotia_duck_tolling_retriever",
      "confidence": 0.02,
      "class_id": 209
    }
  ]
}
```

### NLP Service

#### Text Analysis
```http
POST /ai/nlp/analyze
Content-Type: application/json
Authorization: Bearer <token>

{
  "text": "I love this product! It's amazing and works perfectly.",
  "analysis_types": ["sentiment", "entities", "keywords", "language"],
  "language": "auto"
}
```

**Response:**
```json
{
  "request_id": "req_321654987",
  "text_length": 58,
  "detected_language": "en",
  "sentiment": {
    "polarity": 0.8,
    "subjectivity": 0.7,
    "label": "positive",
    "confidence": 0.92
  },
  "entities": [
    {
      "text": "product",
      "label": "PRODUCT",
      "start": 12,
      "end": 19,
      "confidence": 0.85
    }
  ],
  "keywords": [
    {
      "text": "love",
      "relevance": 0.9,
      "sentiment": 0.8
    },
    {
      "text": "amazing",
      "relevance": 0.8,
      "sentiment": 0.9
    }
  ]
}
```

#### Text Summarization
```http
POST /ai/nlp/summarize
Content-Type: application/json
Authorization: Bearer <token>

{
  "text": "Long article text goes here...",
  "max_length": 100,
  "min_length": 30,
  "model": "bart-large-cnn"
}
```

**Response:**
```json
{
  "request_id": "req_654987321",
  "original_length": 1500,
  "summary": "This is a concise summary of the main points...",
  "summary_length": 85,
  "compression_ratio": 0.057
}
```

## 🔧 Job Management API

### Create Job
```http
POST /jobs
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Batch Image Analysis",
  "type": "batch_processing",
  "service": "vision",
  "parameters": {
    "input_source": "s3://bucket/images/",
    "analysis_type": "object_detection",
    "model": "yolo-v8",
    "output_format": "json"
  },
  "priority": "normal",
  "scheduled_at": "2024-01-01T12:00:00Z"
}
```

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "name": "Batch Image Analysis", 
  "status": "queued",
  "created_at": "2024-01-01T10:00:00Z",
  "estimated_completion": "2024-01-01T13:00:00Z",
  "priority": "normal"
}
```

### Get Job Status
```http
GET /jobs/{job_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "name": "Batch Image Analysis",
  "status": "running",
  "progress": {
    "completed": 45,
    "total": 100,
    "percentage": 45.0
  },
  "created_at": "2024-01-01T10:00:00Z",
  "started_at": "2024-01-01T10:05:00Z",
  "estimated_completion": "2024-01-01T12:30:00Z",
  "results_available": false,
  "logs": [
    {
      "timestamp": "2024-01-01T10:05:15Z",
      "level": "INFO",
      "message": "Processing started"
    }
  ]
}
```

### List Jobs
```http
GET /jobs?status=running&limit=10&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_abc123def456",
      "name": "Batch Image Analysis",
      "status": "running",
      "progress": 45.0,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 25,
    "has_more": true
  }
}
```

### Cancel Job
```http
DELETE /jobs/{job_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "status": "cancelled",
  "cancelled_at": "2024-01-01T11:30:00Z",
  "message": "Job cancelled successfully"
}
```

## 🏥 Health & System API

### System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "2.0.0",
  "services": {
    "orchestrator": {
      "status": "healthy",
      "response_time": 0.015,
      "uptime": 86400
    },
    "llm_service": {
      "status": "healthy", 
      "response_time": 0.234,
      "models_loaded": 3,
      "queue_size": 2
    },
    "vision_service": {
      "status": "healthy",
      "response_time": 0.156,
      "gpu_utilization": 45.6
    },
    "nlp_service": {
      "status": "healthy",
      "response_time": 0.089,
      "memory_usage": "2.1GB"
    }
  }
}
```

### Detailed Health Check
```http
GET /health/comprehensive
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "system_metrics": {
    "cpu_usage": 34.5,
    "memory_usage": 67.8,
    "disk_usage": 23.1,
    "network_io": {
      "bytes_sent": 1234567890,
      "bytes_received": 9876543210
    }
  },
  "database": {
    "status": "connected",
    "connection_pool": {
      "active": 5,
      "idle": 15,
      "max": 20
    }
  },
  "external_services": {
    "model_registry": "healthy",
    "monitoring": "healthy",
    "storage": "healthy"
  }
}
```

### System Metrics
```http
GET /metrics
Authorization: Bearer <token>
```

**Response:**
```prometheus
# HELP aisemble_requests_total Total number of requests
# TYPE aisemble_requests_total counter
aisemble_requests_total{service="llm",status="success"} 12345
aisemble_requests_total{service="vision",status="success"} 6789

# HELP aisemble_request_duration_seconds Request duration in seconds
# TYPE aisemble_request_duration_seconds histogram
aisemble_request_duration_seconds_bucket{service="llm",le="0.1"} 1000
aisemble_request_duration_seconds_bucket{service="llm",le="0.5"} 4500
```

## 🛠️ Operations API

### System Status
```http
GET /ops/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "system_status": "operational",
  "uptime": "7d 14h 32m",
  "active_jobs": 23,
  "queued_jobs": 5,
  "failed_jobs_24h": 2,
  "resource_utilization": {
    "cpu": 45.6,
    "memory": 67.8,
    "gpu": 78.9
  },
  "alerts": [
    {
      "level": "warning",
      "message": "High memory usage detected",
      "timestamp": "2024-01-01T11:45:00Z"
    }
  ]
}
```

### Start/Stop Services
```http
POST /ops/services/{service_name}/start
Authorization: Bearer <token>

{
  "force": false,
  "wait_for_health": true
}
```

**Response:**
```json
{
  "service": "llm_service",
  "action": "start",
  "status": "starting",
  "message": "Service start initiated"
}
```

### View Logs
```http
GET /ops/logs?service=llm&level=error&limit=100
Authorization: Bearer <token>
```

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "ERROR",
      "service": "llm_service",
      "message": "Model loading failed",
      "trace_id": "trace_123",
      "details": {
        "model": "gpt-3.5-turbo",
        "error_code": "MODEL_NOT_FOUND"
      }
    }
  ],
  "pagination": {
    "limit": 100,
    "has_more": false,
    "next_cursor": null
  }
}
```

## 📊 Model Management API

### List Models
```http
GET /models
Authorization: Bearer <token>
```

**Response:**
```json
{
  "models": [
    {
      "id": "gpt-3.5-turbo",
      "name": "GPT-3.5 Turbo",
      "type": "language_model",
      "version": "1.0.0",
      "status": "loaded",
      "capabilities": ["text_generation", "chat"],
      "parameters": {
        "max_tokens": 4096,
        "context_length": 4096
      },
      "performance": {
        "avg_response_time": 1.234,
        "requests_per_hour": 1500
      }
    }
  ]
}
```

### Load Model
```http
POST /models/{model_id}/load
Authorization: Bearer <token>

{
  "force_reload": false,
  "gpu_device": 0
}
```

**Response:**
```json
{
  "model_id": "gpt-3.5-turbo",
  "status": "loading",
  "estimated_time": 30,
  "message": "Model loading initiated"
}
```

### Model Performance
```http
GET /models/{model_id}/performance
Authorization: Bearer <token>
```

**Response:**
```json
{
  "model_id": "gpt-3.5-turbo",
  "performance_metrics": {
    "requests_total": 10000,
    "avg_response_time": 1.234,
    "p95_response_time": 2.567,
    "success_rate": 99.8,
    "error_rate": 0.2,
    "throughput_per_hour": 1500
  },
  "resource_usage": {
    "memory_mb": 2048,
    "gpu_memory_mb": 4096,
    "cpu_percent": 15.6
  }
}
```

## 🔍 Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request body is invalid",
    "details": {
      "field": "model",
      "reason": "Model not found"
    },
    "request_id": "req_123456789",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid authentication token |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `INVALID_REQUEST` | 400 | Request body or parameters are invalid |
| `RATE_LIMIT_EXCEEDED` | 429 | API rate limit exceeded |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `MODEL_NOT_LOADED` | 422 | Requested model is not loaded |
| `QUOTA_EXCEEDED` | 402 | Usage quota exceeded |

## 🔄 Rate Limiting

API requests are subject to rate limiting:

- **Tier 1 (Free)**: 100 requests/hour
- **Tier 2 (Pro)**: 1,000 requests/hour  
- **Tier 3 (Enterprise)**: 10,000 requests/hour

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641024000
```

## 📝 Webhook Support

### Register Webhook
```http
POST /webhooks
Content-Type: application/json
Authorization: Bearer <token>

{
  "url": "https://your-app.com/webhooks/ai-semble",
  "events": ["job.completed", "job.failed", "model.loaded"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload Example
```json
{
  "event": "job.completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "job_id": "job_abc123def456",
    "status": "completed",
    "results_url": "/jobs/job_abc123def456/results"
  }
}
```

## 🔧 SDK & Libraries

### Python SDK
```python
from aisemble import Client

client = Client(
    base_url="https://your-domain.com/api/v2",
    api_key="your_api_key"
)

# Generate text
response = client.llm.generate(
    prompt="Explain quantum computing",
    model="gpt-3.5-turbo",
    max_tokens=500
)

print(response.generated_text)
```

### Node.js SDK
```javascript
const { AiSembleClient } = require('@aisemble/client');

const client = new AiSembleClient({
  baseUrl: 'https://your-domain.com/api/v2',
  apiKey: 'your_api_key'
});

// Analyze image
const result = await client.vision.analyze({
  image: imageBuffer,
  analysisType: ['object_detection', 'text_extraction']
});

console.log(result.analysis_results);
```

## 🚀 Getting Started

1. **Obtain API credentials** from the Ai-semble dashboard
2. **Set up authentication** using JWT tokens
3. **Choose your integration method** (REST API, SDK, or webhooks)
4. **Start with health checks** to verify connectivity
5. **Test with simple requests** before implementing complex workflows

## 📞 Support

- **Documentation**: https://docs.aisemble.ai
- **API Status**: https://status.aisemble.ai
- **Support Email**: support@aisemble.ai
- **GitHub Issues**: https://github.com/aisemble/aisemble-v2/issues

---

*For more detailed examples and tutorials, see the [API Examples](./API_EXAMPLES.md) documentation.*