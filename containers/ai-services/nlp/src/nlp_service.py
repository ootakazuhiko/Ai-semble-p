"""
NLP Service
自然言語処理サービス
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import structlog
from typing import Optional, Dict, Any, List
import re
import string
from collections import Counter
import numpy as np

# 基本的なNLP処理用
try:
    import nltk
    from textblob import TextBlob
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    NLP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some NLP libraries not available: {e}")
    NLP_AVAILABLE = False

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
    title="Ai-semble NLP Service",
    description="自然言語処理サービス",
    version="2.0.0"
)

# NLTKデータの初期化
if NLP_AVAILABLE:
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
    except Exception as e:
        logger.warning("nltk_download_failed", error=str(e))

class NLPRequest(BaseModel):
    """NLP処理リクエスト"""
    text: str
    task: str = "analyze"
    language: str = "auto"
    options: Optional[Dict[str, Any]] = {}

class NLPResponse(BaseModel):
    """NLP処理レスポンス"""
    task: str
    results: Dict[str, Any]
    language_detected: str
    processing_time: float

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "nlp",
        "nltk_available": NLP_AVAILABLE,
        "models_loaded": True
    }

@app.post("/process", response_model=NLPResponse)
async def process_text(request: NLPRequest):
    """テキスト処理実行"""
    import time
    start_time = time.time()
    
    logger.info(
        "nlp_request_received",
        task=request.task,
        text_length=len(request.text),
        language=request.language
    )
    
    try:
        # 言語検出
        detected_language = detect_language(request.text)
        
        # タスクに応じた処理実行
        if request.task == "analyze":
            results = await analyze_text(request.text, request.options)
        elif request.task == "sentiment":
            results = await analyze_sentiment(request.text, request.options)
        elif request.task == "keywords":
            results = await extract_keywords(request.text, request.options)
        elif request.task == "entities":
            results = await extract_entities(request.text, request.options)
        elif request.task == "summarize":
            results = await summarize_text(request.text, request.options)
        elif request.task == "similarity":
            results = await calculate_similarity(request.text, request.options)
        elif request.task == "tokenize":
            results = await tokenize_text(request.text, request.options)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown task: {request.task}"
            )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "nlp_request_completed",
            task=request.task,
            processing_time=processing_time,
            language_detected=detected_language
        )
        
        return NLPResponse(
            task=request.task,
            results=results,
            language_detected=detected_language,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(
            "nlp_request_failed",
            task=request.task,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"NLP processing failed: {e}"
        )

def detect_language(text: str) -> str:
    """言語検出（簡易版）"""
    # 基本的な言語検出
    if NLP_AVAILABLE:
        try:
            blob = TextBlob(text)
            return blob.detect_language()
        except:
            pass
    
    # フォールバック: 文字コードベースの簡易判定
    if any(ord(char) > 127 for char in text):
        if any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' for char in text):
            return "ja"
        elif any('\u4e00' <= char <= '\u9fff' for char in text):
            return "zh"
        elif any('\uAC00' <= char <= '\uD7AF' for char in text):
            return "ko"
    return "en"

async def analyze_text(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """包括的なテキスト分析"""
    analysis = {}
    
    # 基本統計
    words = text.split()
    sentences = text.split('.')
    
    analysis["statistics"] = {
        "character_count": len(text),
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "avg_word_length": np.mean([len(word) for word in words]) if words else 0,
        "avg_sentence_length": len(words) / len(sentences) if sentences else 0
    }
    
    # 文字種分析
    analysis["character_analysis"] = {
        "uppercase_count": sum(1 for c in text if c.isupper()),
        "lowercase_count": sum(1 for c in text if c.islower()),
        "digit_count": sum(1 for c in text if c.isdigit()),
        "punctuation_count": sum(1 for c in text if c in string.punctuation)
    }
    
    # 頻度分析
    word_freq = Counter(word.lower().strip(string.punctuation) for word in words)
    analysis["word_frequency"] = dict(word_freq.most_common(10))
    
    # 感情分析（基本版）
    if NLP_AVAILABLE:
        try:
            blob = TextBlob(text)
            analysis["sentiment"] = {
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity
            }
        except:
            analysis["sentiment"] = {"polarity": 0.0, "subjectivity": 0.0}
    
    return analysis

async def analyze_sentiment(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """感情分析"""
    if not NLP_AVAILABLE:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
            "error": "NLP libraries not available"
        }
    
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # 感情ラベル判定
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # 信頼度計算（主観性の逆数）
        confidence = 1.0 - subjectivity if subjectivity < 1.0 else 0.1
        
        return {
            "sentiment": sentiment,
            "confidence": float(confidence),
            "scores": {
                "polarity": float(polarity),
                "subjectivity": float(subjectivity)
            },
            "details": {
                "positive_words": count_positive_words(text),
                "negative_words": count_negative_words(text)
            }
        }
        
    except Exception as e:
        logger.warning("sentiment_analysis_fallback", error=str(e))
        return basic_sentiment_analysis(text)

def basic_sentiment_analysis(text: str) -> Dict[str, Any]:
    """基本的な感情分析（辞書ベース）"""
    positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "like", "happy"]
    negative_words = ["bad", "terrible", "awful", "horrible", "hate", "dislike", "sad", "angry", "disappointed"]
    
    words = text.lower().split()
    pos_count = sum(1 for word in words if word in positive_words)
    neg_count = sum(1 for word in words if word in negative_words)
    
    if pos_count > neg_count:
        sentiment = "positive"
        confidence = min(0.8, pos_count / len(words) * 10)
    elif neg_count > pos_count:
        sentiment = "negative"
        confidence = min(0.8, neg_count / len(words) * 10)
    else:
        sentiment = "neutral"
        confidence = 0.5
    
    return {
        "sentiment": sentiment,
        "confidence": float(confidence),
        "scores": {
            "positive_count": pos_count,
            "negative_count": neg_count
        }
    }

def count_positive_words(text: str) -> int:
    """ポジティブ単語のカウント"""
    positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "like", "happy"]
    return sum(1 for word in text.lower().split() if word in positive_words)

def count_negative_words(text: str) -> int:
    """ネガティブ単語のカウント"""
    negative_words = ["bad", "terrible", "awful", "horrible", "hate", "dislike", "sad", "angry", "disappointed"]
    return sum(1 for word in text.lower().split() if word in negative_words)

async def extract_keywords(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """キーワード抽出"""
    max_keywords = options.get("max_keywords", 10)
    
    # ストップワードの定義
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should"}
    
    # 単語の前処理
    words = re.findall(r'\b\w+\b', text.lower())
    words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # 頻度ベースのキーワード抽出
    word_freq = Counter(words)
    keywords = [{"word": word, "frequency": freq, "score": freq/len(words)} 
                for word, freq in word_freq.most_common(max_keywords)]
    
    # TF-IDFベースのキーワード抽出（1文書なので簡易版）
    if NLP_AVAILABLE and len(words) > 5:
        try:
            sentences = text.split('.')
            if len(sentences) > 1:
                vectorizer = TfidfVectorizer(stop_words='english', max_features=max_keywords)
                tfidf_matrix = vectorizer.fit_transform(sentences)
                feature_names = vectorizer.get_feature_names_out()
                tfidf_scores = tfidf_matrix.sum(axis=0).A1
                
                tfidf_keywords = [{"word": feature_names[i], "tfidf_score": float(tfidf_scores[i])} 
                                 for i in tfidf_scores.argsort()[::-1][:max_keywords]]
                
                return {
                    "frequency_based": keywords,
                    "tfidf_based": tfidf_keywords,
                    "method": "combined"
                }
        except Exception as e:
            logger.warning("tfidf_extraction_failed", error=str(e))
    
    return {
        "keywords": keywords,
        "method": "frequency_based"
    }

async def extract_entities(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """エンティティ抽出（基本版）"""
    entities = []
    
    # 基本的なパターンマッチング
    # メールアドレス
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    for email in emails:
        entities.append({"text": email, "label": "EMAIL", "confidence": 0.9})
    
    # URL
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    for url in urls:
        entities.append({"text": url, "label": "URL", "confidence": 0.95})
    
    # 電話番号（基本パターン）
    phone_pattern = r'\b\d{3}-\d{3}-\d{4}\b|\b\d{10}\b'
    phones = re.findall(phone_pattern, text)
    for phone in phones:
        entities.append({"text": phone, "label": "PHONE", "confidence": 0.8})
    
    # 日付（基本パターン）
    date_pattern = r'\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b'
    dates = re.findall(date_pattern, text)
    for date in dates:
        entities.append({"text": date, "label": "DATE", "confidence": 0.85})
    
    # 数値
    number_pattern = r'\b\d+\.?\d*\b'
    numbers = re.findall(number_pattern, text)
    for number in numbers[:5]:  # 最大5個まで
        entities.append({"text": number, "label": "NUMBER", "confidence": 0.7})
    
    return {
        "entities": entities,
        "count": len(entities),
        "types": list(set(entity["label"] for entity in entities))
    }

async def summarize_text(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """テキスト要約（抽出型）"""
    max_sentences = options.get("max_sentences", 3)
    
    # 文に分割
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    
    if len(sentences) <= max_sentences:
        return {
            "summary": text,
            "original_sentences": len(sentences),
            "summary_sentences": len(sentences),
            "compression_ratio": 1.0
        }
    
    # 文の重要度計算（単語頻度ベース）
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = Counter(words)
    
    sentence_scores = []
    for i, sentence in enumerate(sentences):
        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
        score = sum(word_freq[word] for word in sentence_words if word in word_freq)
        sentence_scores.append((score, i, sentence))
    
    # スコア順にソート
    sentence_scores.sort(reverse=True)
    
    # 上位文を選択（元の順序を保持）
    selected_sentences = sorted(sentence_scores[:max_sentences], key=lambda x: x[1])
    summary = '. '.join([s[2] for s in selected_sentences]) + '.'
    
    return {
        "summary": summary,
        "original_sentences": len(sentences),
        "summary_sentences": len(selected_sentences),
        "compression_ratio": len(selected_sentences) / len(sentences)
    }

async def calculate_similarity(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """テキスト類似度計算"""
    compare_text = options.get("compare_text", "")
    
    if not compare_text:
        return {
            "error": "compare_text option is required for similarity calculation"
        }
    
    # 単語ベースの類似度（Jaccard係数）
    words1 = set(re.findall(r'\b\w+\b', text.lower()))
    words2 = set(re.findall(r'\b\w+\b', compare_text.lower()))
    
    jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2)) if words1.union(words2) else 0
    
    # 文字レベルの類似度
    char_similarity = calculate_char_similarity(text, compare_text)
    
    result = {
        "jaccard_similarity": float(jaccard_similarity),
        "character_similarity": float(char_similarity),
        "word_overlap": len(words1.intersection(words2)),
        "total_unique_words": len(words1.union(words2))
    }
    
    # TF-IDF類似度（可能な場合）
    if NLP_AVAILABLE:
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([text, compare_text])
            cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            result["tfidf_similarity"] = float(cosine_sim)
        except Exception as e:
            logger.warning("tfidf_similarity_failed", error=str(e))
    
    return result

def calculate_char_similarity(text1: str, text2: str) -> float:
    """文字レベルの類似度計算（簡易版）"""
    # レーベンシュタイン距離の簡易版
    if len(text1) == 0 or len(text2) == 0:
        return 0.0
    
    # 正規化
    text1 = text1.lower().replace(' ', '')
    text2 = text2.lower().replace(' ', '')
    
    # 共通文字数
    common_chars = sum(1 for c1, c2 in zip(text1, text2) if c1 == c2)
    max_len = max(len(text1), len(text2))
    
    return common_chars / max_len if max_len > 0 else 0.0

async def tokenize_text(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """テキストトークン化"""
    # 単語トークン化
    word_tokens = re.findall(r'\b\w+\b', text)
    
    # 文トークン化
    sentence_tokens = [s.strip() for s in text.split('.') if s.strip()]
    
    # 品詞タグ付け（基本版）
    pos_tags = []
    if NLP_AVAILABLE:
        try:
            import nltk
            tokens_with_pos = nltk.pos_tag(word_tokens)
            pos_tags = [{"word": word, "pos": pos} for word, pos in tokens_with_pos]
        except Exception as e:
            logger.warning("pos_tagging_failed", error=str(e))
    
    return {
        "word_tokens": word_tokens,
        "sentence_tokens": sentence_tokens,
        "pos_tags": pos_tags,
        "token_count": len(word_tokens),
        "sentence_count": len(sentence_tokens)
    }

if __name__ == "__main__":
    uvicorn.run(
        "nlp_service:app",
        host="0.0.0.0",
        port=8083,
        log_level="info"
    )