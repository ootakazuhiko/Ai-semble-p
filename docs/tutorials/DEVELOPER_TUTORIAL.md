# Ai-semble v2 Developer Tutorial

## 🎯 Welcome to Ai-semble v2

This comprehensive tutorial will guide you through building applications with Ai-semble v2, from basic setup to advanced AI integrations.

## 📚 Table of Contents

1. [Getting Started](#getting-started)
2. [Your First AI Request](#your-first-ai-request)
3. [Building a Chat Application](#building-a-chat-application)
4. [Image Analysis Pipeline](#image-analysis-pipeline)
5. [Batch Processing](#batch-processing)
6. [Advanced Integrations](#advanced-integrations)
7. [Production Deployment](#production-deployment)

## 🚀 Getting Started

### Prerequisites

- Python 3.8+ or Node.js 16+
- Docker/Podman installed
- Basic understanding of REST APIs
- API keys from Ai-semble dashboard

### Installation

#### Option 1: Python SDK
```bash
pip install aisemble-sdk
```

#### Option 2: Node.js SDK
```bash
npm install @aisemble/client
```

#### Option 3: Direct REST API
No installation required - use any HTTP client!

### Initial Setup

#### Python Setup
```python
from aisemble import Client
import os

# Initialize client
client = Client(
    base_url="http://localhost:8080/api/v2",  # or your production URL
    api_key=os.getenv("AISEMBLE_API_KEY")
)

# Test connection
health = client.health.check()
print(f"Status: {health.status}")
```

#### Node.js Setup
```javascript
const { AiSembleClient } = require('@aisemble/client');

// Initialize client
const client = new AiSembleClient({
  baseUrl: 'http://localhost:8080/api/v2',
  apiKey: process.env.AISEMBLE_API_KEY
});

// Test connection
async function testConnection() {
  const health = await client.health.check();
  console.log(`Status: ${health.status}`);
}
```

## 🤖 Your First AI Request

### Simple Text Generation

#### Python Example
```python
from aisemble import Client

client = Client(base_url="http://localhost:8080/api/v2", api_key="your_key")

# Generate text
response = client.llm.generate(
    prompt="Write a haiku about programming",
    model="gpt-3.5-turbo",
    max_tokens=100,
    temperature=0.7
)

print(response.generated_text)
print(f"Tokens used: {response.metadata.tokens_used}")
print(f"Cost: ${response.metadata.cost:.4f}")
```

#### Node.js Example
```javascript
async function generateText() {
  try {
    const response = await client.llm.generate({
      prompt: "Write a haiku about programming",
      model: "gpt-3.5-turbo",
      maxTokens: 100,
      temperature: 0.7
    });
    
    console.log(response.generatedText);
    console.log(`Tokens used: ${response.metadata.tokensUsed}`);
    console.log(`Cost: $${response.metadata.cost.toFixed(4)}`);
  } catch (error) {
    console.error('Error:', error.message);
  }
}
```

#### curl Example
```bash
curl -X POST http://localhost:8080/api/v2/ai/llm/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "prompt": "Write a haiku about programming",
    "model": "gpt-3.5-turbo",
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

### Error Handling

#### Python
```python
from aisemble import Client, AiSembleError

try:
    response = client.llm.generate(
        prompt="Hello world",
        model="nonexistent-model"
    )
except AiSembleError as e:
    print(f"Error {e.status_code}: {e.message}")
    if e.details:
        print(f"Details: {e.details}")
```

#### Node.js
```javascript
try {
  const response = await client.llm.generate({
    prompt: "Hello world",
    model: "nonexistent-model"
  });
} catch (error) {
  if (error.statusCode) {
    console.error(`API Error ${error.statusCode}: ${error.message}`);
  } else {
    console.error('Network Error:', error.message);
  }
}
```

## 💬 Building a Chat Application

### Simple Chat Bot

#### Python Implementation
```python
import asyncio
from aisemble import Client

class ChatBot:
    def __init__(self, api_key, model="gpt-3.5-turbo"):
        self.client = Client(
            base_url="http://localhost:8080/api/v2",
            api_key=api_key
        )
        self.model = model
        self.conversation_history = []
    
    def add_message(self, role, content):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    async def chat(self, user_message):
        """Send a message and get response"""
        # Add user message to history
        self.add_message("user", user_message)
        
        try:
            # Send to AI
            response = await self.client.llm.chat_async(
                messages=self.conversation_history,
                model=self.model,
                temperature=0.7,
                max_tokens=500
            )
            
            # Add AI response to history
            ai_message = response.choices[0].message.content
            self.add_message("assistant", ai_message)
            
            return ai_message
            
        except Exception as e:
            return f"Sorry, I encountered an error: {e}"
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

# Usage example
async def main():
    bot = ChatBot(api_key="your_key")
    
    print("Chat Bot started! Type 'quit' to exit.")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            break
        
        response = await bot.chat(user_input)
        print(f"Bot: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Web Interface (Flask)
```python
from flask import Flask, render_template, request, jsonify
from aisemble import Client

app = Flask(__name__)
client = Client(base_url="http://localhost:8080/api/v2", api_key="your_key")

# Store conversations (in production, use a database)
conversations = {}

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    user_message = data.get('message')
    
    # Get or create conversation history
    if session_id not in conversations:
        conversations[session_id] = [
            {"role": "system", "content": "You are a helpful AI assistant."}
        ]
    
    # Add user message
    conversations[session_id].append({
        "role": "user", 
        "content": user_message
    })
    
    try:
        # Get AI response
        response = client.llm.chat(
            messages=conversations[session_id],
            model="gpt-3.5-turbo",
            temperature=0.7
        )
        
        ai_message = response.choices[0].message.content
        
        # Add AI response to history
        conversations[session_id].append({
            "role": "assistant",
            "content": ai_message
        })
        
        return jsonify({
            "success": True,
            "message": ai_message,
            "tokens_used": response.usage.total_tokens
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
```

#### HTML Template (chat.html)
```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Chat</title>
    <style>
        .chat-container { max-width: 600px; margin: 50px auto; }
        .messages { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
        .message { margin: 10px 0; }
        .user { text-align: right; color: blue; }
        .assistant { text-align: left; color: green; }
        .input-container { margin-top: 10px; }
        #messageInput { width: 80%; padding: 10px; }
        #sendButton { width: 15%; padding: 10px; }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>AI Chat Interface</h1>
        <div id="messages" class="messages"></div>
        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
            <button id="sendButton" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const sessionId = Math.random().toString(36).substring(7);
        
        function addMessage(role, content) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.innerHTML = `<strong>${role === 'user' ? 'You' : 'AI'}:</strong> ${content}`;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage('user', message);
            input.value = '';
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        message: message
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage('assistant', data.message);
                } else {
                    addMessage('assistant', `Error: ${data.error}`);
                }
            } catch (error) {
                addMessage('assistant', `Network error: ${error.message}`);
            }
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
    </script>
</body>
</html>
```

## 🖼️ Image Analysis Pipeline

### Basic Image Analysis

#### Python Example
```python
import base64
from aisemble import Client

class ImageAnalyzer:
    def __init__(self, api_key):
        self.client = Client(
            base_url="http://localhost:8080/api/v2",
            api_key=api_key
        )
    
    def analyze_image(self, image_path, analysis_types=None):
        """Analyze an image file"""
        if analysis_types is None:
            analysis_types = ["object_detection", "text_extraction", "scene_analysis"]
        
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        try:
            response = self.client.vision.analyze(
                image=image_data,
                analysis_types=analysis_types,
                model="yolo-v8"
            )
            
            return response
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return None
    
    def batch_analyze(self, image_paths):
        """Analyze multiple images"""
        results = []
        
        for path in image_paths:
            print(f"Analyzing {path}...")
            result = self.analyze_image(path)
            if result:
                results.append({
                    'file': path,
                    'analysis': result
                })
        
        return results
    
    def extract_objects(self, analysis_result):
        """Extract object information from analysis"""
        objects = []
        
        if 'analysis_results' in analysis_result:
            for obj in analysis_result['analysis_results'].get('objects', []):
                objects.append({
                    'class': obj['class'],
                    'confidence': obj['confidence'],
                    'bbox': obj['bbox']
                })
        
        return objects

# Usage example
analyzer = ImageAnalyzer(api_key="your_key")

# Analyze single image
result = analyzer.analyze_image("sample.jpg")
if result:
    print(f"Found {len(result.analysis_results.objects)} objects")
    for obj in result.analysis_results.objects:
        print(f"- {obj.class}: {obj.confidence:.2%}")

# Batch analysis
image_files = ["image1.jpg", "image2.jpg", "image3.jpg"]
batch_results = analyzer.batch_analyze(image_files)
```

### Real-time Image Processing

#### Python with OpenCV
```python
import cv2
import numpy as np
from aisemble import Client

class RealTimeAnalyzer:
    def __init__(self, api_key):
        self.client = Client(
            base_url="http://localhost:8080/api/v2",
            api_key=api_key
        )
        self.cap = None
    
    def start_camera(self, camera_index=0):
        """Start camera capture"""
        self.cap = cv2.VideoCapture(camera_index)
        return self.cap.isOpened()
    
    def process_frame(self, frame):
        """Process a single frame"""
        # Convert frame to bytes
        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = buffer.tobytes()
        
        try:
            # Analyze with AI
            result = self.client.vision.analyze(
                image=image_bytes,
                analysis_types=["object_detection"],
                model="yolo-v8"
            )
            
            # Draw bounding boxes
            annotated_frame = self.draw_detections(frame, result)
            return annotated_frame, result
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return frame, None
    
    def draw_detections(self, frame, result):
        """Draw detection boxes on frame"""
        if not result or 'analysis_results' not in result:
            return frame
        
        for obj in result['analysis_results'].get('objects', []):
            # Extract bounding box coordinates
            x1, y1, x2, y2 = obj['bbox']
            
            # Draw rectangle
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Add label
            label = f"{obj['class']}: {obj['confidence']:.2%}"
            cv2.putText(frame, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
    
    def run_live_analysis(self, process_every_n_frames=30):
        """Run live analysis on camera feed"""
        if not self.start_camera():
            print("Could not open camera")
            return
        
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Process every N frames to avoid overwhelming the API
            if frame_count % process_every_n_frames == 0:
                annotated_frame, result = self.process_frame(frame)
                
                # Display results
                if result:
                    num_objects = len(result.get('analysis_results', {}).get('objects', []))
                    cv2.putText(annotated_frame, f"Objects: {num_objects}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                frame = annotated_frame
            
            # Display frame
            cv2.imshow('AI-semble Live Analysis', frame)
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            frame_count += 1
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()

# Usage
analyzer = RealTimeAnalyzer(api_key="your_key")
analyzer.run_live_analysis()
```

## ⚙️ Batch Processing

### Large-Scale Document Processing

#### Python Implementation
```python
import asyncio
import aiofiles
from pathlib import Path
from aisemble import AsyncClient

class DocumentProcessor:
    def __init__(self, api_key, max_concurrent=5):
        self.client = AsyncClient(
            base_url="http://localhost:8080/api/v2",
            api_key=api_key
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_document(self, file_path):
        """Process a single document"""
        async with self.semaphore:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                # Analyze text
                analysis = await self.client.nlp.analyze(
                    text=content,
                    analysis_types=["sentiment", "entities", "keywords", "summary"]
                )
                
                return {
                    'file': str(file_path),
                    'status': 'success',
                    'analysis': analysis,
                    'word_count': len(content.split())
                }
                
            except Exception as e:
                return {
                    'file': str(file_path),
                    'status': 'error',
                    'error': str(e)
                }
    
    async def process_directory(self, directory_path, pattern="*.txt"):
        """Process all files in a directory"""
        directory = Path(directory_path)
        files = list(directory.glob(pattern))
        
        print(f"Found {len(files)} files to process")
        
        # Process files concurrently
        tasks = [self.process_document(file_path) for file_path in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect statistics
        successful = sum(1 for r in results if isinstance(r, dict) and r['status'] == 'success')
        failed = len(results) - successful
        
        print(f"Processing complete: {successful} successful, {failed} failed")
        
        return results
    
    async def create_batch_job(self, job_config):
        """Create a batch processing job"""
        job = await self.client.jobs.create(
            name=job_config['name'],
            type="batch_processing",
            service=job_config['service'],
            parameters=job_config['parameters']
        )
        
        return job
    
    async def monitor_job(self, job_id, check_interval=10):
        """Monitor job progress"""
        while True:
            job_status = await self.client.jobs.get(job_id)
            
            print(f"Job {job_id}: {job_status.status} - {job_status.progress.percentage:.1f}%")
            
            if job_status.status in ['completed', 'failed', 'cancelled']:
                break
            
            await asyncio.sleep(check_interval)
        
        return job_status

# Usage example
async def main():
    processor = DocumentProcessor(api_key="your_key")
    
    # Process local files
    results = await processor.process_directory("./documents", "*.txt")
    
    # Create batch job for large dataset
    job_config = {
        'name': 'Document Analysis Batch',
        'service': 'nlp',
        'parameters': {
            'input_source': 's3://my-bucket/documents/',
            'analysis_types': ['sentiment', 'entities'],
            'output_format': 'json'
        }
    }
    
    job = await processor.create_batch_job(job_config)
    print(f"Created job: {job.job_id}")
    
    # Monitor job
    final_status = await processor.monitor_job(job.job_id)
    print(f"Job completed with status: {final_status.status}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Data Pipeline with Webhooks

#### Python Flask Webhook Handler
```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)
WEBHOOK_SECRET = "your_webhook_secret"

class WebhookHandler:
    def __init__(self):
        self.completed_jobs = []
        self.failed_jobs = []
    
    def verify_signature(self, payload, signature):
        """Verify webhook signature"""
        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    def handle_job_completed(self, data):
        """Handle job completion"""
        job_id = data['job_id']
        print(f"Job {job_id} completed successfully")
        
        # Download results
        self.download_results(job_id)
        
        # Trigger next step in pipeline
        self.trigger_post_processing(job_id)
    
    def handle_job_failed(self, data):
        """Handle job failure"""
        job_id = data['job_id']
        error = data.get('error', 'Unknown error')
        
        print(f"Job {job_id} failed: {error}")
        
        # Log failure
        self.log_failure(job_id, error)
        
        # Possibly retry or alert
        self.handle_failure_recovery(job_id)
    
    def download_results(self, job_id):
        """Download job results"""
        # Implementation depends on your storage setup
        print(f"Downloading results for job {job_id}")
    
    def trigger_post_processing(self, job_id):
        """Trigger next pipeline step"""
        print(f"Starting post-processing for job {job_id}")
    
    def log_failure(self, job_id, error):
        """Log job failure"""
        with open('failed_jobs.log', 'a') as f:
            f.write(f"{job_id}: {error}\n")
    
    def handle_failure_recovery(self, job_id):
        """Handle failure recovery"""
        # Implement retry logic or alerting
        pass

webhook_handler = WebhookHandler()

@app.route('/webhooks/aisemble', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not webhook_handler.verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse payload
    payload = request.json
    event_type = payload.get('event')
    data = payload.get('data', {})
    
    # Handle different event types
    if event_type == 'job.completed':
        webhook_handler.handle_job_completed(data)
    elif event_type == 'job.failed':
        webhook_handler.handle_job_failed(data)
    else:
        print(f"Unhandled event type: {event_type}")
    
    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 🔧 Advanced Integrations

### Custom Model Integration

#### Adding Your Own Model
```python
from aisemble import Client
import torch
from transformers import AutoModel, AutoTokenizer

class CustomModelWrapper:
    def __init__(self, model_path, api_key):
        self.client = Client(
            base_url="http://localhost:8080/api/v2",
            api_key=api_key
        )
        
        # Load your custom model
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)
    
    def register_model(self):
        """Register your model with Ai-semble"""
        model_config = {
            "id": "my-custom-model",
            "name": "My Custom Model",
            "type": "language_model",
            "capabilities": ["text_classification", "text_generation"],
            "parameters": {
                "max_tokens": 2048,
                "context_length": 4096
            }
        }
        
        return self.client.models.register(model_config)
    
    def predict(self, text):
        """Make prediction with custom model"""
        inputs = self.tokenizer(text, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Process outputs according to your model
        return outputs

# Usage
wrapper = CustomModelWrapper("./my-model", "your_key")
wrapper.register_model()
```

### Multi-Service Orchestration

#### Complex AI Workflow
```python
import asyncio
from aisemble import AsyncClient

class AIWorkflow:
    def __init__(self, api_key):
        self.client = AsyncClient(
            base_url="http://localhost:8080/api/v2",
            api_key=api_key
        )
    
    async def analyze_document_with_images(self, document_path, image_paths):
        """Comprehensive document and image analysis"""
        
        # Step 1: Extract text from document
        with open(document_path, 'r') as f:
            document_text = f.read()
        
        # Step 2: Analyze document text
        text_analysis = await self.client.nlp.analyze(
            text=document_text,
            analysis_types=["sentiment", "entities", "summary"]
        )
        
        # Step 3: Analyze images concurrently
        image_tasks = [
            self.client.vision.analyze(
                image=open(img_path, 'rb').read(),
                analysis_types=["object_detection", "text_extraction"]
            )
            for img_path in image_paths
        ]
        
        image_analyses = await asyncio.gather(*image_tasks)
        
        # Step 4: Generate comprehensive report using LLM
        report_prompt = self.create_report_prompt(
            document_text, text_analysis, image_analyses
        )
        
        report = await self.client.llm.generate(
            prompt=report_prompt,
            model="gpt-4",
            max_tokens=1000
        )
        
        return {
            'document_analysis': text_analysis,
            'image_analyses': image_analyses,
            'comprehensive_report': report.generated_text
        }
    
    def create_report_prompt(self, text, text_analysis, image_analyses):
        """Create prompt for comprehensive report"""
        prompt = f"""
        Based on the following analysis results, create a comprehensive report:
        
        Document Summary: {text_analysis.get('summary', '')}
        Document Sentiment: {text_analysis.get('sentiment', {}).get('label', '')}
        
        Key Entities:
        """
        
        for entity in text_analysis.get('entities', []):
            prompt += f"- {entity['text']} ({entity['label']})\n"
        
        prompt += "\nImage Analysis Results:\n"
        for i, img_analysis in enumerate(image_analyses):
            objects = img_analysis.get('analysis_results', {}).get('objects', [])
            prompt += f"Image {i+1}: Found {len(objects)} objects\n"
        
        prompt += "\nPlease provide a coherent analysis combining all these insights."
        
        return prompt

# Usage
async def main():
    workflow = AIWorkflow(api_key="your_key")
    
    result = await workflow.analyze_document_with_images(
        "report.txt",
        ["chart1.png", "chart2.png", "diagram.jpg"]
    )
    
    print("Comprehensive Analysis Complete!")
    print(result['comprehensive_report'])

asyncio.run(main())
```

## 🚀 Production Deployment

### Environment Configuration

#### Production Settings
```python
# config/production.py
import os

class ProductionConfig:
    # API Configuration
    AISEMBLE_BASE_URL = os.getenv('AISEMBLE_BASE_URL', 'https://api.aisemble.ai/v2')
    AISEMBLE_API_KEY = os.getenv('AISEMBLE_API_KEY')
    
    # Rate Limiting
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2
    
    # Caching
    CACHE_TTL = 300  # 5 minutes
    CACHE_BACKEND = 'redis'
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Monitoring
    ENABLE_METRICS = True
    METRICS_PORT = 9090
    
    # Security
    VERIFY_SSL = True
    API_KEY_ROTATION_DAYS = 30
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = 'json'

# Client with production settings
from aisemble import Client

client = Client(
    base_url=ProductionConfig.AISEMBLE_BASE_URL,
    api_key=ProductionConfig.AISEMBLE_API_KEY,
    timeout=ProductionConfig.REQUEST_TIMEOUT,
    max_retries=ProductionConfig.MAX_RETRIES,
    verify_ssl=ProductionConfig.VERIFY_SSL
)
```

### Error Handling & Monitoring

#### Robust Error Handling
```python
import logging
import time
from functools import wraps
from aisemble import Client, AiSembleError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, backoff=2):
    """Decorator for automatic retries"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except AiSembleError as e:
                    if e.status_code >= 500 and attempt < max_retries - 1:
                        wait_time = backoff ** attempt
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                        continue
                    raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff ** attempt
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                        continue
                    raise
            
        return wrapper
    return decorator

class ProductionAIService:
    def __init__(self, api_key):
        self.client = Client(
            base_url="https://api.aisemble.ai/v2",
            api_key=api_key
        )
    
    @retry_on_failure(max_retries=3)
    async def generate_text_safe(self, prompt, **kwargs):
        """Generate text with error handling and monitoring"""
        start_time = time.time()
        
        try:
            response = await self.client.llm.generate(prompt=prompt, **kwargs)
            
            # Log success metrics
            duration = time.time() - start_time
            logger.info(f"Text generation successful", extra={
                'duration': duration,
                'tokens_used': response.metadata.tokens_used,
                'model': kwargs.get('model', 'default')
            })
            
            return response
            
        except AiSembleError as e:
            # Log API errors
            logger.error(f"AI service error", extra={
                'error_code': e.status_code,
                'error_message': e.message,
                'prompt_length': len(prompt)
            })
            raise
            
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in text generation: {e}")
            raise

# Usage
service = ProductionAIService(api_key="your_key")
```

### Performance Optimization

#### Caching and Connection Pooling
```python
import asyncio
import aioredis
from aisemble import AsyncClient

class OptimizedAIService:
    def __init__(self, api_key, redis_url="redis://localhost:6379"):
        self.client = AsyncClient(
            base_url="https://api.aisemble.ai/v2",
            api_key=api_key,
            connection_pool_size=20
        )
        self.redis = None
    
    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url(self.redis_url)
    
    async def get_cached_response(self, cache_key):
        """Get cached response from Redis"""
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        return None
    
    async def cache_response(self, cache_key, response, ttl=300):
        """Cache response in Redis"""
        if self.redis:
            await self.redis.setex(
                cache_key, 
                ttl, 
                json.dumps(response, default=str)
            )
    
    async def generate_with_cache(self, prompt, **kwargs):
        """Generate text with caching"""
        # Create cache key
        cache_key = f"llm:{hash(prompt)}:{hash(str(kwargs))}"
        
        # Check cache first
        cached = await self.get_cached_response(cache_key)
        if cached:
            return cached
        
        # Generate new response
        response = await self.client.llm.generate(prompt=prompt, **kwargs)
        
        # Cache the response
        await self.cache_response(cache_key, response)
        
        return response

# Batch processing optimization
class BatchProcessor:
    def __init__(self, api_key, batch_size=10):
        self.client = AsyncClient(api_key=api_key)
        self.batch_size = batch_size
    
    async def process_batch(self, items, processor_func):
        """Process items in batches"""
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # Process batch concurrently
            batch_tasks = [processor_func(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            results.extend(batch_results)
            
            # Optional: add delay between batches to respect rate limits
            if i + self.batch_size < len(items):
                await asyncio.sleep(0.1)
        
        return results
```

## 🎓 Best Practices

### 1. API Key Management
```python
import os
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self.key = os.environ.get('ENCRYPTION_KEY')
        if not self.key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        
        self.cipher = Fernet(self.key.encode())
    
    def get_api_key(self):
        encrypted_key = os.environ.get('AISEMBLE_API_KEY_ENCRYPTED')
        if encrypted_key:
            return self.cipher.decrypt(encrypted_key.encode()).decode()
        
        # Fallback to plain key (not recommended for production)
        return os.environ.get('AISEMBLE_API_KEY')
```

### 2. Rate Limiting Compliance
```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests=100, time_window=3600):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.now()
        
        # Remove old requests outside time window
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < timedelta(seconds=self.time_window)
        ]
        
        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request).total_seconds()
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.requests.append(now)
```

### 3. Testing Your Integration
```python
import pytest
from unittest.mock import Mock, patch
from aisemble import Client

class TestAIIntegration:
    def setup_method(self):
        self.client = Client(
            base_url="http://localhost:8080/api/v2",
            api_key="test_key"
        )
    
    @patch('aisemble.Client.llm.generate')
    def test_text_generation(self, mock_generate):
        # Mock response
        mock_response = Mock()
        mock_response.generated_text = "Test response"
        mock_response.metadata.tokens_used = 10
        mock_generate.return_value = mock_response
        
        # Test
        result = self.client.llm.generate(prompt="Test prompt")
        
        # Assertions
        assert result.generated_text == "Test response"
        assert result.metadata.tokens_used == 10
        mock_generate.assert_called_once_with(prompt="Test prompt")
    
    def test_error_handling(self):
        with patch('aisemble.Client.llm.generate') as mock_generate:
            mock_generate.side_effect = Exception("API Error")
            
            with pytest.raises(Exception):
                self.client.llm.generate(prompt="Test")
```

## 🔗 Next Steps

1. **Explore Advanced Features**: Webhooks, batch processing, custom models
2. **Optimize Performance**: Implement caching, connection pooling
3. **Monitor Usage**: Set up logging, metrics, and alerting
4. **Scale Your Application**: Deploy with proper load balancing
5. **Stay Updated**: Follow the [API changelog](https://docs.aisemble.ai/changelog)

## 📞 Getting Help

- **Documentation**: https://docs.aisemble.ai
- **API Reference**: [API_REFERENCE.md](../api/API_REFERENCE.md)
- **Community Forum**: https://community.aisemble.ai
- **GitHub Issues**: https://github.com/aisemble/aisemble-v2/issues
- **Support Email**: developers@aisemble.ai

Happy coding with Ai-semble v2! 🚀