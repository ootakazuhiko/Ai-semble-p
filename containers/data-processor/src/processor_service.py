"""
Data Processor Service
データ処理サービス
"""
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import pandas as pd
import structlog
from typing import Dict, Any, Optional, List
import json
import os
import aiofiles

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
    title="Ai-semble Data Processor",
    description="データ処理サービス",
    version="2.0.0"
)

class ProcessRequest(BaseModel):
    """データ処理リクエスト"""
    operation: str
    data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = {}

class ProcessResponse(BaseModel):
    """データ処理レスポンス"""
    status: str
    result: Dict[str, Any]
    rows_processed: int
    processing_time: float

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "data-processor",
        "data_dir": "/data"
    }

@app.post("/process", response_model=ProcessResponse)
async def process_data(request: ProcessRequest):
    """データ処理実行"""
    import time
    start_time = time.time()
    
    logger.info(
        "data_processing_started",
        operation=request.operation,
        data_size=len(str(request.data))
    )
    
    try:
        if request.operation == "analyze":
            result = await analyze_data(request.data, request.options)
        elif request.operation == "transform":
            result = await transform_data(request.data, request.options)
        elif request.operation == "aggregate":
            result = await aggregate_data(request.data, request.options)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation: {request.operation}"
            )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "data_processing_completed",
            operation=request.operation,
            processing_time=processing_time,
            rows_processed=result.get("rows_processed", 0)
        )
        
        return ProcessResponse(
            status="completed",
            result=result,
            rows_processed=result.get("rows_processed", 0),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(
            "data_processing_failed",
            operation=request.operation,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Data processing failed: {e}"
        )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """ファイルアップロード"""
    try:
        file_path = f"/data/{file.filename}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(
            "file_uploaded",
            filename=file.filename,
            size=len(content)
        )
        
        return {
            "filename": file.filename,
            "size": len(content),
            "path": file_path
        }
        
    except Exception as e:
        logger.error(
            "file_upload_failed",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {e}"
        )

async def analyze_data(data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """データ分析"""
    # データをDataFrameに変換
    if "records" in data:
        df = pd.DataFrame(data["records"])
    else:
        df = pd.DataFrame(data)
    
    analysis_result = {
        "shape": df.shape,
        "dtypes": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "numeric_summary": {},
        "rows_processed": len(df)
    }
    
    # 数値列の統計情報
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        analysis_result["numeric_summary"] = df[numeric_cols].describe().to_dict()
    
    return analysis_result

async def transform_data(data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """データ変換"""
    if "records" in data:
        df = pd.DataFrame(data["records"])
    else:
        df = pd.DataFrame(data)
    
    # 変換オプションに基づく処理
    if options.get("normalize"):
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = (df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std()
    
    if options.get("drop_na"):
        df = df.dropna()
    
    if options.get("columns"):
        df = df[options["columns"]]
    
    return {
        "transformed_data": df.to_dict("records"),
        "rows_processed": len(df)
    }

async def aggregate_data(data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """データ集約"""
    if "records" in data:
        df = pd.DataFrame(data["records"])
    else:
        df = pd.DataFrame(data)
    
    group_by = options.get("group_by", [])
    agg_funcs = options.get("agg_funcs", {"count": "size"})
    
    if group_by:
        result_df = df.groupby(group_by).agg(agg_funcs).reset_index()
    else:
        result_df = df.agg(agg_funcs)
    
    return {
        "aggregated_data": result_df.to_dict("records") if hasattr(result_df, 'to_dict') else result_df.to_dict(),
        "rows_processed": len(df)
    }

if __name__ == "__main__":
    uvicorn.run(
        "processor_service:app",
        host="0.0.0.0",
        port=8084,
        log_level="info"
    )