"""
LLM バッチ処理システム
複数のリクエストを効率的にバッチ処理
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import structlog
import torch
import numpy as np

logger = structlog.get_logger()

@dataclass
class BatchRequest:
    """バッチリクエスト項目"""
    id: str
    prompt: str
    kwargs: Dict[str, Any]
    future: asyncio.Future
    timestamp: float

class BatchProcessor:
    """LLM推論のバッチ処理器"""
    
    def __init__(self, 
                 max_batch_size: int = 4,
                 max_wait_time: float = 0.1,
                 max_sequence_length: int = 512):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.max_sequence_length = max_sequence_length
        
        self.pending_requests: List[BatchRequest] = []
        self.processing_task: Optional[asyncio.Task] = None
        self.model = None
        self.tokenizer = None
        
        logger.info("batch_processor_initialized",
                   max_batch_size=max_batch_size,
                   max_wait_time=max_wait_time)
    
    def set_model(self, model, tokenizer):
        """モデルとトークナイザーを設定"""
        self.model = model
        self.tokenizer = tokenizer
    
    async def add_request(self, request_id: str, prompt: str, **kwargs) -> str:
        """リクエストをバッチキューに追加"""
        future = asyncio.Future()
        batch_request = BatchRequest(
            id=request_id,
            prompt=prompt,
            kwargs=kwargs,
            future=future,
            timestamp=time.time()
        )
        
        self.pending_requests.append(batch_request)
        
        logger.debug("request_added_to_batch",
                    request_id=request_id,
                    queue_size=len(self.pending_requests))
        
        # バッチ処理開始
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_batch_loop())
        
        try:
            result = await future
            return result
        except Exception as e:
            logger.error("batch_request_failed", request_id=request_id, error=str(e))
            raise
    
    async def _process_batch_loop(self):
        """バッチ処理ループ"""
        while self.pending_requests:
            try:
                await self._wait_for_batch()
                if self.pending_requests:
                    await self._process_current_batch()
            except Exception as e:
                logger.error("batch_processing_error", error=str(e))
                # エラー時は待機中の全リクエストにエラーを通知
                await self._fail_pending_requests(e)
                break
    
    async def _wait_for_batch(self):
        """バッチが準備できるまで待機"""
        start_time = time.time()
        
        while (len(self.pending_requests) < self.max_batch_size and 
               time.time() - start_time < self.max_wait_time and
               self.pending_requests):
            await asyncio.sleep(0.01)  # 10ms間隔でチェック
    
    async def _process_current_batch(self):
        """現在のバッチを処理"""
        if not self.pending_requests:
            return
        
        # バッチサイズ分のリクエストを取得
        batch = self.pending_requests[:self.max_batch_size]
        self.pending_requests = self.pending_requests[self.max_batch_size:]
        
        batch_size = len(batch)
        batch_start_time = time.time()
        
        logger.info("batch_processing_started",
                   batch_size=batch_size,
                   remaining_queue=len(self.pending_requests))
        
        try:
            if self.model is None or self.tokenizer is None:
                raise RuntimeError("Model or tokenizer not initialized")
            
            # バッチ推論実行
            results = await self._batch_inference(batch)
            
            processing_time = time.time() - batch_start_time
            
            # 結果を各Futureに設定
            for request, result in zip(batch, results):
                if not request.future.done():
                    request.future.set_result(result)
            
            logger.info("batch_processing_completed",
                       batch_size=batch_size,
                       processing_time=processing_time,
                       avg_time_per_request=processing_time/batch_size)
                       
        except Exception as e:
            logger.error("batch_inference_failed",
                        batch_size=batch_size,
                        error=str(e))
            
            # エラー時は全てのFutureにエラーを設定
            for request in batch:
                if not request.future.done():
                    request.future.set_exception(e)
    
    async def _batch_inference(self, batch: List[BatchRequest]) -> List[str]:
        """バッチ推論実行"""
        prompts = [req.prompt for req in batch]
        
        # プロンプトをトークン化
        # パディングを有効にしてバッチ処理
        encoded_inputs = self.tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_sequence_length
        )
        
        # GPU使用時はデバイスに移動
        device = next(self.model.parameters()).device
        input_ids = encoded_inputs['input_ids'].to(device)
        attention_mask = encoded_inputs['attention_mask'].to(device)
        
        # 推論パラメータ統一 (最初のリクエストの設定を使用)
        first_kwargs = batch[0].kwargs
        max_new_tokens = first_kwargs.get('max_tokens', 100)
        temperature = first_kwargs.get('temperature', 0.7)
        top_p = first_kwargs.get('top_p', 0.9)
        
        # バッチ推論実行
        with torch.no_grad():
            if hasattr(torch, 'cuda') and torch.cuda.is_available():
                with torch.cuda.amp.autocast():
                    outputs = self.model.generate(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id,
                        use_cache=True
                    )
            else:
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=True
                )
        
        # 結果をデコード
        results = []
        for i, (output, request) in enumerate(zip(outputs, batch)):
            # 入力プロンプト部分を除去
            input_length = input_ids[i].shape[0]
            generated_tokens = output[input_length:]
            
            # デコード
            generated_text = self.tokenizer.decode(
                generated_tokens, 
                skip_special_tokens=True
            ).strip()
            
            results.append(generated_text)
        
        return results
    
    async def _fail_pending_requests(self, error: Exception):
        """待機中の全リクエストにエラーを通知"""
        for request in self.pending_requests:
            if not request.future.done():
                request.future.set_exception(error)
        self.pending_requests.clear()
    
    async def shutdown(self):
        """バッチ処理器をシャットダウン"""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # 残りのリクエストをキャンセル
        for request in self.pending_requests:
            if not request.future.done():
                request.future.cancel()
        
        self.pending_requests.clear()
        logger.info("batch_processor_shutdown")