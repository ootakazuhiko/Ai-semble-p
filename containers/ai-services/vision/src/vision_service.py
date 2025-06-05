"""
Vision Service
画像解析・コンピュータビジョンサービス
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import cv2
import numpy as np
from PIL import Image
import requests
import structlog
from typing import Optional, Dict, Any, List
import base64
import io
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
    title="Ai-semble Vision Service",
    description="画像解析・コンピュータビジョンサービス",
    version="2.0.0"
)

class VisionRequest(BaseModel):
    """画像解析リクエスト"""
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    task: str = "analyze"
    options: Optional[Dict[str, Any]] = {}

class VisionResponse(BaseModel):
    """画像解析レスポンス"""
    analysis_type: str
    results: Dict[str, Any]
    confidence: float
    processing_time: float

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "vision",
        "opencv_version": cv2.__version__,
        "models_loaded": True
    }

@app.post("/analyze", response_model=VisionResponse)
async def analyze_image(request: VisionRequest):
    """画像解析実行"""
    import time
    start_time = time.time()
    
    logger.info(
        "vision_request_received",
        task=request.task,
        has_url=bool(request.image_url),
        has_base64=bool(request.image_base64)
    )
    
    try:
        # 画像データ取得
        image = await load_image(request.image_url, request.image_base64)
        
        # タスクに応じた解析実行
        if request.task == "analyze":
            results = await analyze_general(image, request.options)
        elif request.task == "detect_objects":
            results = await detect_objects(image, request.options)
        elif request.task == "extract_text":
            results = await extract_text(image, request.options)
        elif request.task == "classify":
            results = await classify_image(image, request.options)
        elif request.task == "face_detection":
            results = await detect_faces(image, request.options)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown task: {request.task}"
            )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "vision_request_completed",
            task=request.task,
            processing_time=processing_time,
            results_count=len(results.get("detections", []))
        )
        
        return VisionResponse(
            analysis_type=request.task,
            results=results,
            confidence=results.get("confidence", 0.0),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(
            "vision_request_failed",
            task=request.task,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Vision analysis failed: {e}"
        )

async def load_image(image_url: Optional[str], image_base64: Optional[str]) -> np.ndarray:
    """画像データを読み込み"""
    if image_url:
        # URL から画像をダウンロード
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image_data = response.content
    elif image_base64:
        # Base64 から画像をデコード
        image_data = base64.b64decode(image_base64)
    else:
        raise ValueError("Either image_url or image_base64 must be provided")
    
    # PILで画像を読み込み
    pil_image = Image.open(io.BytesIO(image_data))
    
    # OpenCV形式に変換
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return opencv_image

async def analyze_general(image: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
    """一般的な画像解析"""
    height, width = image.shape[:2]
    
    # 基本的な画像情報
    analysis = {
        "dimensions": {"width": width, "height": height},
        "channels": image.shape[2] if len(image.shape) == 3 else 1,
        "aspect_ratio": round(width / height, 2)
    }
    
    # 色彩分析
    if len(image.shape) == 3:
        # 平均色算出
        mean_color = np.mean(image.reshape(-1, 3), axis=0)
        analysis["average_color"] = {
            "r": int(mean_color[2]),
            "g": int(mean_color[1]), 
            "b": int(mean_color[0])
        }
        
        # 明度分析
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        analysis["brightness"] = {
            "mean": float(np.mean(gray)),
            "std": float(np.std(gray))
        }
    
    # エッジ検出
    if options.get("detect_edges", True):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (width * height)
        analysis["edge_density"] = float(edge_density)
    
    analysis["confidence"] = 0.95
    return analysis

async def detect_objects(image: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
    """オブジェクト検出（基本的な輪郭検出）"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # ガウシアンブラーとしきい値処理
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, threshold = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
    
    # 輪郭検出
    contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 最小面積でフィルタリング
    min_area = options.get("min_area", 100)
    objects = []
    
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            objects.append({
                "id": i,
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "area": float(area),
                "confidence": min(0.8, area / 1000)  # 簡易的な信頼度
            })
    
    return {
        "detections": objects,
        "count": len(objects),
        "confidence": 0.75
    }

async def extract_text(image: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
    """テキスト抽出（基本的な前処理のみ）"""
    # グレースケール変換
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # ノイズ除去とコントラスト改善
    denoised = cv2.fastNlMeansDenoising(gray)
    enhanced = cv2.equalizeHist(denoised)
    
    # この実装では実際のOCRは行わず、前処理結果を返す
    text_regions = []
    
    # テキスト領域候補の検出（簡易版）
    edges = cv2.Canny(enhanced, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h
        
        # テキスト領域らしい矩形をフィルタリング
        if 0.1 < aspect_ratio < 10 and w > 20 and h > 10:
            text_regions.append({
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "text": "[OCR処理が必要]",  # 実際のOCRエンジンが必要
                "confidence": 0.6
            })
    
    return {
        "text_regions": text_regions,
        "extracted_text": "実際のOCRエンジン（Tesseract等）の統合が必要です",
        "confidence": 0.6
    }

async def classify_image(image: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
    """画像分類（基本的な特徴分析）"""
    height, width = image.shape[:2]
    
    # 簡易的な分類（実際にはCNNモデルが必要）
    classes = []
    
    # 色彩に基づく簡易分類
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
    dominant_hue = np.argmax(h_hist)
    
    if dominant_hue < 15 or dominant_hue > 165:
        classes.append({"label": "red_dominant", "confidence": 0.7})
    elif 15 <= dominant_hue < 45:
        classes.append({"label": "yellow_dominant", "confidence": 0.7})
    elif 45 <= dominant_hue < 75:
        classes.append({"label": "green_dominant", "confidence": 0.7})
    elif 75 <= dominant_hue < 135:
        classes.append({"label": "blue_dominant", "confidence": 0.7})
    
    # 明度に基づく分類
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    
    if mean_brightness < 85:
        classes.append({"label": "dark_image", "confidence": 0.8})
    elif mean_brightness > 170:
        classes.append({"label": "bright_image", "confidence": 0.8})
    
    return {
        "classifications": classes,
        "primary_class": classes[0] if classes else {"label": "unknown", "confidence": 0.1},
        "confidence": classes[0]["confidence"] if classes else 0.1
    }

async def detect_faces(image: np.ndarray, options: Dict[str, Any]) -> Dict[str, Any]:
    """顔検出"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # OpenCVのHaar Cascade分類器を使用
    # 注意: 実際の環境では事前に分類器ファイルが必要
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=options.get("scale_factor", 1.1),
            minNeighbors=options.get("min_neighbors", 5),
            minSize=options.get("min_size", (30, 30))
        )
        
        face_detections = []
        for i, (x, y, w, h) in enumerate(faces):
            face_detections.append({
                "id": i,
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "confidence": 0.85  # Haar cascadeの信頼度は固定値
            })
        
        return {
            "faces": face_detections,
            "count": len(face_detections),
            "confidence": 0.85 if len(face_detections) > 0 else 0.1
        }
        
    except Exception as e:
        logger.warning("face_detection_fallback", error=str(e))
        # フォールバック: 顔検出器が利用できない場合
        return {
            "faces": [],
            "count": 0,
            "confidence": 0.0,
            "error": "Face detection cascade not available"
        }

if __name__ == "__main__":
    uvicorn.run(
        "vision_service:app",
        host="0.0.0.0",
        port=8082,
        log_level="info"
    )