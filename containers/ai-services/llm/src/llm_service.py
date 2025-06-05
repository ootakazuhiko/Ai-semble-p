"""
LLM Service
大規模言語モデル推論サービス
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import structlog
from typing import Optional
import os

# ロギング設定
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

logger = structlog.get_logger()

app = FastAPI(
    title="Ai-semble LLM Service",
    description="大規模言語モデル推論サービス",
    version="2.0.0"
)

# グローバル変数でモデルを保持
tokenizer = None
model = None

class CompletionRequest(BaseModel):
    """テキスト生成リクエスト"""
    prompt: str
    model: Optional[str] = "default"
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9

class CompletionResponse(BaseModel):
    """テキスト生成レスポンス"""
    text: str
    tokens_used: int
    model: str

@app.on_event("startup")
async def load_model():
    """モデル読み込み"""
    global tokenizer, model
    
    model_name = os.getenv("MODEL_NAME", "microsoft/DialoGPT-small")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    logger.info(
        "model_loading_started",
        model_name=model_name,
        device=device
    )
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        if device == "cuda":
            model = model.to(device)
            
        # パディングトークンを設定
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            
        logger.info(
            "model_loaded_successfully",
            model_name=model_name,
            device=device,
            gpu_available=torch.cuda.is_available()
        )
        
    except Exception as e:
        logger.error(
            "model_loading_failed",
            error=str(e),
            model_name=model_name
        )
        raise

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "llm",
        "model_loaded": model is not None,
        "gpu_available": torch.cuda.is_available()
    }

@app.post("/completion", response_model=CompletionResponse)
async def text_completion(request: CompletionRequest):
    """テキスト生成"""
    if model is None or tokenizer is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded"
        )
    
    logger.info(
        "completion_request_received",
        prompt_length=len(request.prompt),
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    try:
        # テキストをトークン化
        inputs = tokenizer.encode(
            request.prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
        
        # テキスト生成
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # デコード
        generated_text = tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        # プロンプト部分を除去
        response_text = generated_text[len(request.prompt):].strip()
        
        logger.info(
            "completion_request_completed",
            response_length=len(response_text),
            tokens_used=len(outputs[0])
        )
        
        return CompletionResponse(
            text=response_text,
            tokens_used=len(outputs[0]),
            model=request.model or "default"
        )
        
    except Exception as e:
        logger.error(
            "completion_request_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Text generation failed: {e}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "llm_service:app",
        host="0.0.0.0",
        port=8081,
        log_level="info"
    )