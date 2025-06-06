#!/usr/bin/env python3
"""
Ai-semble v2 Load Testing and Performance Benchmarking
Comprehensive performance evaluation tool
"""

import asyncio
import aiohttp
import time
import json
import statistics
import argparse
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from concurrent.futures import ThreadPoolExecutor
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Single test result data structure"""
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    response_time: float
    request_size: int
    response_size: int
    success: bool
    error_message: Optional[str] = None

@dataclass
class BenchmarkSummary:
    """Benchmark summary statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_duration: float
    requests_per_second: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    error_rate: float

class SystemMonitor:
    """System resource monitoring during load tests"""
    
    def __init__(self):
        self.cpu_usage = []
        self.memory_usage = []
        self.disk_io = []
        self.network_io = []
        self.timestamps = []
        self.monitoring = False
    
    async def start_monitoring(self, interval=1.0):
        """Start system monitoring"""
        self.monitoring = True
        while self.monitoring:
            try:
                timestamp = datetime.now()
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()
                
                self.timestamps.append(timestamp)
                self.cpu_usage.append(cpu_percent)
                self.memory_usage.append(memory.percent)
                
                if disk_io:
                    self.disk_io.append({
                        'read_bytes': disk_io.read_bytes,
                        'write_bytes': disk_io.write_bytes
                    })
                
                if network_io:
                    self.network_io.append({
                        'bytes_sent': network_io.bytes_sent,
                        'bytes_recv': network_io.bytes_recv
                    })
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
    
    def get_summary(self):
        """Get monitoring summary"""
        if not self.cpu_usage:
            return {}
        
        return {
            'avg_cpu_usage': statistics.mean(self.cpu_usage),
            'max_cpu_usage': max(self.cpu_usage),
            'avg_memory_usage': statistics.mean(self.memory_usage),
            'max_memory_usage': max(self.memory_usage),
            'monitoring_duration': len(self.timestamps),
            'sample_count': len(self.cpu_usage)
        }

class LoadTester:
    """Main load testing class"""
    
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results: List[TestResult] = []
        self.monitor = SystemMonitor()
        
        # Default headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Ai-semble-LoadTester/1.0'
        }
        
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    async def make_request(self, session: aiohttp.ClientSession, 
                          endpoint: str, method: str = 'GET', 
                          data: Dict = None) -> TestResult:
        """Make a single HTTP request and record results"""
        url = f"{self.base_url}{endpoint}"
        request_size = len(json.dumps(data)) if data else 0
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        try:
            async with session.request(
                method, url, 
                json=data if method != 'GET' else None,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_text = await response.text()
                end_time = time.time()
                
                return TestResult(
                    timestamp=timestamp,
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    response_time=end_time - start_time,
                    request_size=request_size,
                    response_size=len(response_text),
                    success=200 <= response.status < 400
                )
                
        except Exception as e:
            end_time = time.time()
            return TestResult(
                timestamp=timestamp,
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time=end_time - start_time,
                request_size=request_size,
                response_size=0,
                success=False,
                error_message=str(e)
            )
    
    async def health_check_test(self, concurrent_users: int = 10, duration: int = 60):
        """Basic health check load test"""
        logger.info(f"Starting health check test: {concurrent_users} users, {duration}s")
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor.start_monitoring())
        
        start_time = time.time()
        tasks = []
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration:
                # Limit concurrent requests
                if len(tasks) < concurrent_users:
                    task = asyncio.create_task(
                        self.make_request(session, '/health', 'GET')
                    )
                    tasks.append(task)
                
                # Collect completed tasks
                if tasks:
                    done, pending = await asyncio.wait(
                        tasks, timeout=0.1, return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in done:
                        result = await task
                        self.results.append(result)
                    
                    tasks = list(pending)
                
                await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning
            
            # Wait for remaining tasks
            if tasks:
                remaining_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in remaining_results:
                    if isinstance(result, TestResult):
                        self.results.append(result)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        await monitor_task
        
        logger.info(f"Health check test completed: {len(self.results)} requests")
    
    async def ai_inference_test(self, concurrent_users: int = 5, requests_per_user: int = 10):
        """AI inference performance test"""
        logger.info(f"Starting AI inference test: {concurrent_users} users, {requests_per_user} requests each")
        
        # Test payloads
        test_payloads = [
            {
                'endpoint': '/ai/llm/generate',
                'data': {
                    'prompt': 'Write a short poem about artificial intelligence',
                    'model': 'gpt-3.5-turbo',
                    'max_tokens': 100,
                    'temperature': 0.7
                }
            },
            {
                'endpoint': '/ai/nlp/analyze',
                'data': {
                    'text': 'This is a sample text for sentiment analysis and entity extraction.',
                    'analysis_types': ['sentiment', 'entities']
                }
            }
        ]
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor.start_monitoring())
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for user_id in range(concurrent_users):
                for request_id in range(requests_per_user):
                    for payload in test_payloads:
                        task = asyncio.create_task(
                            self.make_request(
                                session, 
                                payload['endpoint'], 
                                'POST', 
                                payload['data']
                            )
                        )
                        tasks.append(task)
            
            # Execute all requests
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, TestResult):
                    self.results.append(result)
                else:
                    logger.error(f"Request failed: {result}")
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        await monitor_task
        
        logger.info(f"AI inference test completed: {len(self.results)} requests")
    
    async def stress_test(self, max_users: int = 100, ramp_up_time: int = 60, hold_time: int = 120):
        """Stress test with gradual ramp-up"""
        logger.info(f"Starting stress test: ramp up to {max_users} users over {ramp_up_time}s, hold for {hold_time}s")
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor.start_monitoring())
        
        start_time = time.time()
        current_users = 0
        active_tasks = []
        
        async with aiohttp.ClientSession() as session:
            # Ramp-up phase
            while time.time() - start_time < ramp_up_time:
                target_users = int((time.time() - start_time) / ramp_up_time * max_users)
                
                # Add users
                while current_users < target_users:
                    task = asyncio.create_task(
                        self.stress_user_simulation(session, user_id=current_users)
                    )
                    active_tasks.append(task)
                    current_users += 1
                
                await asyncio.sleep(1)
            
            # Hold phase
            logger.info(f"Holding {max_users} users for {hold_time}s")
            await asyncio.sleep(hold_time)
            
            # Collect results
            logger.info("Collecting stress test results...")
            results = await asyncio.gather(*active_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    self.results.extend(result)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        await monitor_task
        
        logger.info(f"Stress test completed: {len(self.results)} total requests")
    
    async def stress_user_simulation(self, session: aiohttp.ClientSession, user_id: int) -> List[TestResult]:
        """Simulate a single user during stress test"""
        user_results = []
        
        try:
            # Simulate user behavior
            for _ in range(10):  # Each user makes 10 requests
                # Random delay between requests
                await asyncio.sleep(0.5 + (user_id % 3) * 0.2)
                
                # Choose random endpoint
                endpoints = ['/health', '/api/v2/ops/status']
                endpoint = endpoints[user_id % len(endpoints)]
                
                result = await self.make_request(session, endpoint, 'GET')
                user_results.append(result)
                
        except Exception as e:
            logger.error(f"User {user_id} simulation failed: {e}")
        
        return user_results
    
    def calculate_summary(self) -> BenchmarkSummary:
        """Calculate benchmark summary statistics"""
        if not self.results:
            return BenchmarkSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        response_times = [r.response_time for r in successful_results]
        
        if not response_times:
            response_times = [0]
        
        # Calculate time span
        timestamps = [datetime.fromisoformat(r.timestamp) for r in self.results]
        total_duration = (max(timestamps) - min(timestamps)).total_seconds()
        
        return BenchmarkSummary(
            total_requests=len(self.results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            success_rate=len(successful_results) / len(self.results) * 100,
            total_duration=total_duration,
            requests_per_second=len(self.results) / total_duration if total_duration > 0 else 0,
            avg_response_time=statistics.mean(response_times),
            p50_response_time=statistics.median(response_times),
            p95_response_time=self._percentile(response_times, 95),
            p99_response_time=self._percentile(response_times, 99),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            error_rate=len(failed_results) / len(self.results) * 100
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def generate_report(self, output_file: str = None):
        """Generate comprehensive performance report"""
        summary = self.calculate_summary()
        system_summary = self.monitor.get_summary()
        
        report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'total_requests': len(self.results)
            },
            'performance_summary': asdict(summary),
            'system_resources': system_summary,
            'detailed_results': [asdict(r) for r in self.results[-100:]]  # Last 100 results
        }
        
        # Print summary to console
        self._print_summary(summary, system_summary)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {output_file}")
        
        return report
    
    def _print_summary(self, summary: BenchmarkSummary, system_summary: Dict):
        """Print performance summary to console"""
        print("\\n" + "="*60)
        print("           AI-SEMBLE V2 PERFORMANCE REPORT")
        print("="*60)
        
        print(f"\\n📊 LOAD TEST SUMMARY:")
        print(f"   Total Requests: {summary.total_requests:,}")
        print(f"   Successful: {summary.successful_requests:,} ({summary.success_rate:.1f}%)")
        print(f"   Failed: {summary.failed_requests:,} ({summary.error_rate:.1f}%)")
        print(f"   Duration: {summary.total_duration:.1f}s")
        print(f"   Throughput: {summary.requests_per_second:.1f} req/s")
        
        print(f"\\n⏱️  RESPONSE TIMES:")
        print(f"   Average: {summary.avg_response_time*1000:.1f}ms")
        print(f"   Median (P50): {summary.p50_response_time*1000:.1f}ms")
        print(f"   95th Percentile: {summary.p95_response_time*1000:.1f}ms")
        print(f"   99th Percentile: {summary.p99_response_time*1000:.1f}ms")
        print(f"   Min: {summary.min_response_time*1000:.1f}ms")
        print(f"   Max: {summary.max_response_time*1000:.1f}ms")
        
        if system_summary:
            print(f"\\n🖥️  SYSTEM RESOURCES:")
            print(f"   Average CPU: {system_summary.get('avg_cpu_usage', 0):.1f}%")
            print(f"   Peak CPU: {system_summary.get('max_cpu_usage', 0):.1f}%")
            print(f"   Average Memory: {system_summary.get('avg_memory_usage', 0):.1f}%")
            print(f"   Peak Memory: {system_summary.get('max_memory_usage', 0):.1f}%")
        
        print(f"\\n🎯 PERFORMANCE RATING:")
        rating = self._calculate_performance_rating(summary)
        print(f"   Overall Rating: {rating}")
        
        print("="*60 + "\\n")
    
    def _calculate_performance_rating(self, summary: BenchmarkSummary) -> str:
        """Calculate overall performance rating"""
        score = 0
        
        # Success rate (40% weight)
        if summary.success_rate >= 99:
            score += 40
        elif summary.success_rate >= 95:
            score += 30
        elif summary.success_rate >= 90:
            score += 20
        
        # Response time (30% weight)
        if summary.p95_response_time < 0.5:
            score += 30
        elif summary.p95_response_time < 1.0:
            score += 25
        elif summary.p95_response_time < 2.0:
            score += 15
        
        # Throughput (20% weight)
        if summary.requests_per_second > 100:
            score += 20
        elif summary.requests_per_second > 50:
            score += 15
        elif summary.requests_per_second > 20:
            score += 10
        
        # Error rate (10% weight)
        if summary.error_rate < 1:
            score += 10
        elif summary.error_rate < 5:
            score += 5
        
        if score >= 90:
            return "🟢 EXCELLENT"
        elif score >= 70:
            return "🟡 GOOD"
        elif score >= 50:
            return "🟠 FAIR"
        else:
            return "🔴 POOR"
    
    def generate_charts(self, output_dir: str = "."):
        """Generate performance charts"""
        try:
            # Response time over time
            timestamps = [datetime.fromisoformat(r.timestamp) for r in self.results]
            response_times = [r.response_time * 1000 for r in self.results]  # Convert to ms
            
            plt.figure(figsize=(12, 8))
            
            # Response time chart
            plt.subplot(2, 2, 1)
            plt.plot(timestamps, response_times, alpha=0.6)
            plt.title('Response Time Over Time')
            plt.xlabel('Time')
            plt.ylabel('Response Time (ms)')
            plt.xticks(rotation=45)
            
            # Response time histogram
            plt.subplot(2, 2, 2)
            plt.hist([r for r in response_times if r < 5000], bins=50, alpha=0.7)
            plt.title('Response Time Distribution')
            plt.xlabel('Response Time (ms)')
            plt.ylabel('Frequency')
            
            # Success rate over time
            plt.subplot(2, 2, 3)
            success_rates = []
            window_size = max(1, len(self.results) // 20)
            for i in range(0, len(self.results), window_size):
                window = self.results[i:i+window_size]
                success_rate = sum(1 for r in window if r.success) / len(window) * 100
                success_rates.append(success_rate)
            
            window_timestamps = timestamps[::window_size][:len(success_rates)]
            plt.plot(window_timestamps, success_rates, marker='o')
            plt.title('Success Rate Over Time')
            plt.xlabel('Time')
            plt.ylabel('Success Rate (%)')
            plt.xticks(rotation=45)
            plt.ylim(0, 105)
            
            # System resources (if available)
            plt.subplot(2, 2, 4)
            if self.monitor.cpu_usage:
                plt.plot(self.monitor.timestamps, self.monitor.cpu_usage, label='CPU %')
                plt.plot(self.monitor.timestamps, self.monitor.memory_usage, label='Memory %')
                plt.title('System Resources')
                plt.xlabel('Time')
                plt.ylabel('Usage (%)')
                plt.legend()
                plt.xticks(rotation=45)
            else:
                plt.text(0.5, 0.5, 'No system monitoring data', 
                        ha='center', va='center', transform=plt.gca().transAxes)
                plt.title('System Resources')
            
            plt.tight_layout()
            chart_file = f"{output_dir}/performance_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Charts saved to {chart_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Ai-semble v2 Load Testing Tool')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL of Ai-semble instance')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--test-type', choices=['health', 'inference', 'stress', 'all'], 
                       default='health', help='Type of test to run')
    parser.add_argument('--users', type=int, default=10, 
                       help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Test duration in seconds')
    parser.add_argument('--output', help='Output file for detailed results')
    parser.add_argument('--charts', action='store_true', 
                       help='Generate performance charts')
    
    args = parser.parse_args()
    
    # Create load tester
    tester = LoadTester(args.url, args.api_key)
    
    try:
        if args.test_type == 'health' or args.test_type == 'all':
            await tester.health_check_test(args.users, args.duration)
        
        if args.test_type == 'inference' or args.test_type == 'all':
            await tester.ai_inference_test(args.users // 2, 5)
        
        if args.test_type == 'stress' or args.test_type == 'all':
            await tester.stress_test(args.users * 2, 30, 60)
        
        # Generate report
        tester.generate_report(args.output)
        
        # Generate charts if requested
        if args.charts:
            tester.generate_charts()
            
    except KeyboardInterrupt:
        logger.info("Load test interrupted by user")
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())