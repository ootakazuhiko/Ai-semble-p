"""
HTTP接続プール管理
パフォーマンス最適化のための接続プール実装
"""
import httpx
from typing import Optional, Dict, Any
import asyncio
import structlog
from ..config.settings import get_settings

logger = structlog.get_logger()

class HTTPConnectionPool:
    """最適化されたHTTP接続プール"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def get_client(self) -> httpx.AsyncClient:
        """接続プールクライアントを取得"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    await self._create_client()
        return self._client
    
    async def _create_client(self):
        """最適化されたHTTPクライアントを作成"""
        # 接続プール設定
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )
        
        # タイムアウト設定
        timeout = httpx.Timeout(
            timeout=30.0,
            connect=5.0,
            read=25.0,
            write=5.0
        )
        
        # クライアント作成
        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=True,
            follow_redirects=True
        )
        
        logger.info("http_connection_pool_created", 
                   max_connections=100,
                   keepalive_connections=20)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """最適化されたPOSTリクエスト"""
        client = await self.get_client()
        return await client.post(url, **kwargs)
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """最適化されたGETリクエスト"""
        client = await self.get_client()
        return await client.get(url, **kwargs)
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """汎用リクエストメソッド"""
        client = await self.get_client()
        return await client.request(method, url, **kwargs)
    
    async def close(self):
        """接続プールをクローズ"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("http_connection_pool_closed")

# グローバル接続プールインスタンス
_connection_pool: Optional[HTTPConnectionPool] = None

async def get_connection_pool() -> HTTPConnectionPool:
    """グローバル接続プールを取得"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = HTTPConnectionPool()
    return _connection_pool

async def close_connection_pool():
    """グローバル接続プールをクローズ"""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close()
        _connection_pool = None