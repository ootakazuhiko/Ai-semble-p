#!/usr/bin/env python3
"""
Ai-semble v2 パフォーマンス監視スクリプト
"""
import asyncio
import aiohttp
import time
import statistics
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
    
    async def measure_endpoint(self, 
                              endpoint: str, 
                              method: str = "GET",
                              payload: Optional[Dict] = None, 
                              iterations: int = 10,
                              delay: float = 0.1) -> Dict[str, Any]:
        """エンドポイントのパフォーマンス測定"""
        print(f"Testing {method} {endpoint} ({iterations} iterations)...")
        
        response_times = []
        status_codes = []
        errors = []
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for i in range(iterations):
                start_time = time.time()
                try:
                    if method.upper() == "POST" and payload:
                        async with session.post(
                            f"{self.base_url}{endpoint}", 
                            json=payload
                        ) as response:
                            await response.read()
                            status_codes.append(response.status)
                    else:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            await response.read()
                            status_codes.append(response.status)
                            
                except Exception as e:
                    errors.append(str(e))
                    status_codes.append(0)
                    
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                response_times.append(response_time)
                
                if delay > 0:
                    await asyncio.sleep(delay)
                    
                # プログレス表示
                if (i + 1) % max(1, iterations // 10) == 0:
                    print(f"  Progress: {i + 1}/{iterations}")
        
        # 統計計算
        success_count = len([s for s in status_codes if 200 <= s < 400])
        error_count = len(errors)
        
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            # パーセンタイル計算
            sorted_times = sorted(response_times)
            p50 = statistics.median(sorted_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_idx] if p95_idx < len(sorted_times) else max_time
        else:
            avg_time = min_time = max_time = p50 = p95 = 0
        
        result = {
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.now().isoformat(),
            "iterations": iterations,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / iterations * 100) if iterations > 0 else 0,
            "response_times": {
                "avg": round(avg_time, 2),
                "min": round(min_time, 2),
                "max": round(max_time, 2),
                "p50": round(p50, 2),
                "p95": round(p95, 2)
            },
            "errors": errors[:5]  # 最初の5個のエラーのみ保存
        }
        
        print(f"  Completed: {success_count}/{iterations} success, avg: {avg_time:.1f}ms")
        return result
    
    async def run_health_check_test(self, iterations: int = 50) -> Dict[str, Any]:
        """ヘルスチェックエンドポイントテスト"""
        return await self.measure_endpoint(
            "/health", 
            method="GET",
            iterations=iterations,
            delay=0.05
        )
    
    async def run_llm_test(self, iterations: int = 5) -> Dict[str, Any]:
        """LLM推論テスト"""
        payload = {
            "prompt": "Hello, this is a performance test prompt.",
            "max_tokens": 20,
            "temperature": 0.1
        }
        return await self.measure_endpoint(
            "/ai/llm/completion",
            method="POST",
            payload=payload,
            iterations=iterations,
            delay=1.0
        )
    
    async def run_vision_test(self, iterations: int = 10) -> Dict[str, Any]:
        """Vision解析テスト"""
        # 1x1ピクセルの透明PNG (base64)
        test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        payload = {
            "image_base64": test_image,
            "task": "analyze"
        }
        return await self.measure_endpoint(
            "/ai/vision/analyze",
            method="POST",
            payload=payload,
            iterations=iterations,
            delay=0.5
        )
    
    async def run_nlp_test(self, iterations: int = 20) -> Dict[str, Any]:
        """NLP処理テスト"""
        payload = {
            "text": "This is a performance test sentence for NLP processing. It contains various words to analyze.",
            "task": "sentiment"
        }
        return await self.measure_endpoint(
            "/ai/nlp/process",
            method="POST",
            payload=payload,
            iterations=iterations,
            delay=0.2
        )
    
    async def run_data_processor_test(self, iterations: int = 15) -> Dict[str, Any]:
        """データ処理テスト"""
        payload = {
            "operation": "analyze",
            "data": {
                "records": [
                    {"id": i, "value": i * 10, "category": f"cat_{i % 3}"}
                    for i in range(100)
                ]
            }
        }
        return await self.measure_endpoint(
            "/data/process",
            method="POST",
            payload=payload,
            iterations=iterations,
            delay=0.3
        )
    
    async def run_load_test(self, concurrent_users: int = 10, duration: int = 30) -> Dict[str, Any]:
        """負荷テスト"""
        print(f"Running load test: {concurrent_users} concurrent users for {duration} seconds")
        
        start_time = time.time()
        end_time = start_time + duration
        
        async def user_simulation():
            """ユーザーシミュレーション"""
            requests_made = 0
            response_times = []
            errors = 0
            
            connector = aiohttp.TCPConnector(limit=10)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                while time.time() < end_time:
                    try:
                        req_start = time.time()
                        async with session.get(f"{self.base_url}/health") as response:
                            await response.read()
                            if response.status >= 400:
                                errors += 1
                        req_end = time.time()
                        response_times.append((req_end - req_start) * 1000)
                        requests_made += 1
                        await asyncio.sleep(0.1)  # 100ms間隔
                    except Exception:
                        errors += 1
                        
            return {
                "requests_made": requests_made,
                "response_times": response_times,
                "errors": errors
            }
        
        # 並行ユーザーシミュレーション実行
        tasks = [user_simulation() for _ in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)
        
        # 結果集計
        total_requests = sum(r["requests_made"] for r in user_results)
        total_errors = sum(r["errors"] for r in user_results)
        all_response_times = []
        for r in user_results:
            all_response_times.extend(r["response_times"])
        
        actual_duration = time.time() - start_time
        
        return {
            "test_type": "load_test",
            "concurrent_users": concurrent_users,
            "duration": round(actual_duration, 2),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "requests_per_second": round(total_requests / actual_duration, 2),
            "error_rate": round((total_errors / total_requests * 100) if total_requests > 0 else 0, 2),
            "avg_response_time": round(statistics.mean(all_response_times), 2) if all_response_times else 0,
            "p95_response_time": round(statistics.quantiles(all_response_times, n=20)[18], 2) if len(all_response_times) >= 20 else 0
        }
    
    async def comprehensive_benchmark(self) -> Dict[str, Any]:
        """包括的ベンチマーク実行"""
        print("=== Ai-semble v2 Performance Benchmark ===")
        print(f"Target: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")
        print()
        
        benchmark_start = time.time()
        
        # 各テスト実行
        tests = [
            ("Health Check", self.run_health_check_test()),
            ("LLM Completion", self.run_llm_test()),
            ("Vision Analysis", self.run_vision_test()),
            ("NLP Processing", self.run_nlp_test()),
            ("Data Processing", self.run_data_processor_test())
        ]
        
        results = []
        for test_name, test_coro in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = await test_coro
                results.append(result)
            except Exception as e:
                print(f"Error in {test_name}: {e}")
                results.append({
                    "endpoint": test_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # 負荷テスト
        print(f"\n--- Load Test ---")
        try:
            load_test_result = await self.run_load_test(concurrent_users=5, duration=10)
            results.append(load_test_result)
        except Exception as e:
            print(f"Error in load test: {e}")
        
        benchmark_duration = time.time() - benchmark_start
        
        # 全体サマリー生成
        summary = self._generate_summary(results, benchmark_duration)
        
        final_result = {
            "benchmark_info": {
                "timestamp": datetime.now().isoformat(),
                "target_url": self.base_url,
                "duration": round(benchmark_duration, 2)
            },
            "results": results,
            "summary": summary
        }
        
        print("\n=== Summary ===")
        print(f"Total benchmark time: {benchmark_duration:.1f}s")
        print(f"Tests completed: {len([r for r in results if 'error' not in r])}/{len(results)}")
        
        return final_result
    
    def _generate_summary(self, results: List[Dict], duration: float) -> Dict[str, Any]:
        """ベンチマーク結果サマリー生成"""
        successful_tests = [r for r in results if 'response_times' in r]
        
        if not successful_tests:
            return {"status": "All tests failed"}
        
        # 平均レスポンス時間計算
        avg_response_times = []
        total_requests = 0
        total_errors = 0
        
        for result in successful_tests:
            if 'response_times' in result:
                avg_response_times.append(result['response_times']['avg'])
                total_requests += result.get('iterations', 0)
                total_errors += result.get('error_count', 0)
        
        return {
            "status": "completed",
            "successful_tests": len(successful_tests),
            "total_tests": len(results),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "overall_success_rate": round((total_requests - total_errors) / total_requests * 100, 2) if total_requests > 0 else 0,
            "avg_response_time_across_endpoints": round(statistics.mean(avg_response_times), 2) if avg_response_times else 0,
            "benchmark_duration": round(duration, 2)
        }

async def main():
    parser = argparse.ArgumentParser(description="Ai-semble v2 Performance Monitor")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL for testing")
    parser.add_argument("--test", choices=["health", "llm", "vision", "nlp", "data", "load", "all"], 
                       default="all", help="Test type to run")
    parser.add_argument("--iterations", type=int, default=10, help="Number of iterations per test")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent users for load test")
    parser.add_argument("--duration", type=int, default=30, help="Duration for load test (seconds)")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.url)
    
    try:
        if args.test == "all":
            results = await monitor.comprehensive_benchmark()
        elif args.test == "health":
            results = await monitor.run_health_check_test(args.iterations)
        elif args.test == "llm":
            results = await monitor.run_llm_test(args.iterations)
        elif args.test == "vision":
            results = await monitor.run_vision_test(args.iterations)
        elif args.test == "nlp":
            results = await monitor.run_nlp_test(args.iterations)
        elif args.test == "data":
            results = await monitor.run_data_processor_test(args.iterations)
        elif args.test == "load":
            results = await monitor.run_load_test(args.concurrent, args.duration)
        
        # 結果出力
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        else:
            print("\n" + "="*50)
            print(json.dumps(results, indent=2))
            
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())