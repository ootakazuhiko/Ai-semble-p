#!/usr/bin/env python3
"""
Ai-semble v2 運用ダッシュボード
リアルタイム監視・ログ・バックアップ状況の統合ビュー
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import argparse
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class OperationsDashboard:
    """運用ダッシュボード"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None
        self.refresh_interval = 5  # 秒
        self.last_update = None
        
    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.close()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """システム状況取得"""
        try:
            async with self.session.get(f"{self.base_url}/ops/status") as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_log_stats(self) -> Dict[str, Any]:
        """ログ統計取得"""
        try:
            async with self.session.get(f"{self.base_url}/ops/logs/stats?hours=1") as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_backup_status(self) -> Dict[str, Any]:
        """バックアップ状況取得"""
        try:
            async with self.session.get(f"{self.base_url}/ops/backups/status") as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """包括的ヘルスチェック"""
        try:
            async with self.session.get(f"{self.base_url}/ops/health/comprehensive") as response:
                if response.status == 200:
                    return await response.json()
                return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    def create_system_status_panel(self, system_data: Dict[str, Any]) -> Panel:
        """システム状況パネル作成"""
        if "error" in system_data:
            return Panel(f"❌ Error: {system_data['error']}", title="System Status", border_style="red")
        
        status = system_data.get("overall_status", "unknown")
        status_color = "green" if status == "healthy" else "yellow" if status == "degraded" else "red"
        
        # システムメトリクス
        metrics = system_data.get("system_metrics", {})
        cpu = metrics.get("cpu_usage", 0)
        memory = metrics.get("memory_usage", 0)
        disk = metrics.get("disk_usage", 0)
        
        # サービス状況
        services = system_data.get("services", {})
        healthy_services = services.get("healthy", 0)
        total_services = services.get("total", 0)
        
        content = f"""
[{status_color}]Status: {status.upper()}[/{status_color}]
Services: {healthy_services}/{total_services} healthy

System Resources:
  CPU: {cpu:.1f}%
  Memory: {memory:.1f}%
  Disk: {disk:.1f}%

Last Update: {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        return Panel(content, title="🖥️  System Status", border_style=status_color)
    
    def create_services_table(self, system_data: Dict[str, Any]) -> Table:
        """サービス詳細テーブル作成"""
        table = Table(title="🔧 Services Detail")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Response Time", justify="right")
        table.add_column("Last Check", justify="right")
        table.add_column("Failures", justify="right")
        
        if "error" in system_data:
            table.add_row("Error", system_data["error"], "", "", "")
            return table
        
        services_detail = system_data.get("services_detail", {})
        
        for service_name, service_info in services_detail.items():
            status = service_info.get("status", "unknown")
            status_style = "green" if status == "healthy" else "red"
            
            response_time = f"{service_info.get('response_time', 0):.3f}s"
            last_check = service_info.get("last_check", "")
            if last_check:
                last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00')).strftime('%H:%M:%S')
            
            failures = str(service_info.get("consecutive_failures", 0))
            
            table.add_row(
                service_name,
                f"[{status_style}]{status}[/{status_style}]",
                response_time,
                last_check,
                failures
            )
        
        return table
    
    def create_log_stats_panel(self, log_data: Dict[str, Any]) -> Panel:
        """ログ統計パネル作成"""
        if "error" in log_data:
            return Panel(f"❌ Error: {log_data['error']}", title="Log Statistics", border_style="red")
        
        total_entries = log_data.get("total_entries", 0)
        error_rate = log_data.get("error_rate", 0)
        
        # レベル別分布
        level_dist = log_data.get("level_distribution", {})
        errors = level_dist.get("ERROR", 0)
        warnings = level_dist.get("WARNING", 0)
        info = level_dist.get("INFO", 0)
        
        error_color = "red" if error_rate > 5 else "yellow" if error_rate > 1 else "green"
        
        content = f"""
Total Entries (1h): {total_entries:,}
[{error_color}]Error Rate: {error_rate:.1f}%[/{error_color}]

Log Levels:
  INFO: {info:,}
  WARNING: {warnings:,}
  ERROR: {errors:,}

Period: {log_data.get('period', {}).get('hours', 1)}h
        """.strip()
        
        return Panel(content, title="📊 Log Statistics", border_style="blue")
    
    def create_backup_status_panel(self, backup_data: Dict[str, Any]) -> Panel:
        """バックアップ状況パネル作成"""
        if "error" in backup_data:
            return Panel(f"❌ Error: {backup_data['error']}", title="Backup Status", border_style="red")
        
        scheduler_running = backup_data.get("scheduler_running", False)
        scheduler_color = "green" if scheduler_running else "red"
        
        jobs = backup_data.get("jobs", {})
        enabled_jobs = len([j for j in jobs.values() if j.get("enabled", False)])
        total_jobs = len(jobs)
        
        # 最近のバックアップ結果
        recent_results = backup_data.get("recent_results", [])
        successful_recent = len([r for r in recent_results[:5] if r.get("success", False)])
        
        # ストレージ使用量
        storage = backup_data.get("storage_usage", {})
        storage_mb = storage.get("total_size_mb", 0)
        file_count = storage.get("file_count", 0)
        
        content = f"""
[{scheduler_color}]Scheduler: {"Running" if scheduler_running else "Stopped"}[/{scheduler_color}]
Jobs: {enabled_jobs}/{total_jobs} enabled

Recent Success: {successful_recent}/5
Storage: {storage_mb:.1f} MB ({file_count} files)

Last Update: {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        return Panel(content, title="💾 Backup Status", border_style="cyan")
    
    def create_alerts_panel(self, system_data: Dict[str, Any]) -> Panel:
        """アラートパネル作成"""
        if "error" in system_data:
            return Panel(f"❌ Error: {system_data['error']}", title="Recent Alerts", border_style="red")
        
        recent_alerts = system_data.get("recent_alerts", [])
        
        if not recent_alerts:
            content = "[green]✅ No recent alerts[/green]"
        else:
            alert_lines = []
            for alert in recent_alerts[-5:]:  # 最新5件
                timestamp = alert.get("timestamp", "")
                if timestamp:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%H:%M')
                
                rule_name = alert.get("rule_name", "Unknown")
                severity = alert.get("severity", "info")
                severity_color = "red" if severity == "critical" else "yellow" if severity == "warning" else "blue"
                
                alert_lines.append(f"[{severity_color}]{timestamp} {rule_name}[/{severity_color}]")
            
            content = "\n".join(alert_lines)
        
        return Panel(content, title="🚨 Recent Alerts", border_style="yellow")
    
    def create_health_summary(self, health_data: Dict[str, Any]) -> Panel:
        """ヘルスサマリーパネル作成"""
        if "error" in health_data:
            return Panel(f"❌ Error: {health_data['error']}", title="Health Summary", border_style="red")
        
        overall_health = health_data.get("overall_health", "unknown")
        health_color = "green" if overall_health == "healthy" else "yellow" if overall_health == "degraded" else "red"
        
        issues = health_data.get("issues", [])
        
        content = f"[{health_color}]Overall Health: {overall_health.upper()}[/{health_color}]\n\n"
        
        if issues:
            content += "Issues:\n"
            for issue in issues:
                content += f"  ⚠️  {issue}\n"
        else:
            content += "[green]✅ All systems operational[/green]"
        
        content += f"\nChecked: {datetime.now().strftime('%H:%M:%S')}"
        
        return Panel(content, title="🩺 Health Summary", border_style=health_color)
    
    async def create_dashboard_layout(self) -> Layout:
        """ダッシュボードレイアウト作成"""
        # データ取得
        system_data = await self.get_system_status()
        log_data = await self.get_log_stats()
        backup_data = await self.get_backup_status()
        health_data = await self.get_comprehensive_health()
        
        # レイアウト作成
        layout = Layout()
        
        # 上部: ヘルスサマリー
        layout.split_column(
            Layout(name="header", size=7),
            Layout(name="main", size=20),
            Layout(name="bottom", size=8)
        )
        
        # ヘッダー: ヘルスサマリー
        layout["header"].update(self.create_health_summary(health_data))
        
        # メイン部分を3列に分割
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="center"),
            Layout(name="right")
        )
        
        # 左列: システム状況
        layout["left"].split_column(
            Layout(self.create_system_status_panel(system_data), name="system"),
            Layout(self.create_log_stats_panel(log_data), name="logs")
        )
        
        # 中央列: サービス詳細
        layout["center"].update(self.create_services_table(system_data))
        
        # 右列: バックアップとアラート
        layout["right"].split_column(
            Layout(self.create_backup_status_panel(backup_data), name="backup"),
            Layout(self.create_alerts_panel(system_data), name="alerts")
        )
        
        # 下部: フッター
        footer_text = f"Ai-semble v2 Operations Dashboard | Refresh: {self.refresh_interval}s | Press Ctrl+C to exit"
        layout["bottom"].update(Panel(footer_text, style="dim"))
        
        self.last_update = datetime.now()
        return layout
    
    async def run_dashboard(self):
        """ダッシュボード実行"""
        console.print("[bold blue]Ai-semble v2 Operations Dashboard[/bold blue]")
        console.print(f"Connecting to: {self.base_url}")
        console.print("Press Ctrl+C to exit\n")
        
        try:
            with Live(auto_refresh=False) as live:
                while True:
                    try:
                        layout = await self.create_dashboard_layout()
                        live.update(layout, refresh=True)
                        await asyncio.sleep(self.refresh_interval)
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        error_panel = Panel(f"❌ Dashboard Error: {e}", border_style="red")
                        live.update(error_panel, refresh=True)
                        await asyncio.sleep(self.refresh_interval)
                        
        except KeyboardInterrupt:
            pass
        
        console.print("\n[yellow]Dashboard stopped[/yellow]")
    
    async def run_simple_status(self):
        """シンプルな状況表示"""
        console.print("[bold blue]Ai-semble v2 System Status[/bold blue]")
        console.print(f"Checking: {self.base_url}\n")
        
        health_data = await self.get_comprehensive_health()
        
        if "error" in health_data:
            console.print(f"[red]❌ Error: {health_data['error']}[/red]")
            return
        
        overall_health = health_data.get("overall_health", "unknown")
        health_color = "green" if overall_health == "healthy" else "yellow" if overall_health == "degraded" else "red"
        
        console.print(f"Overall Health: [{health_color}]{overall_health.upper()}[/{health_color}]")
        
        issues = health_data.get("issues", [])
        if issues:
            console.print("\nIssues:")
            for issue in issues:
                console.print(f"  ⚠️  {issue}")
        else:
            console.print("[green]✅ All systems operational[/green]")
        
        # システムメトリクス表示
        system_status = health_data.get("system_status", {})
        system_metrics = system_status.get("system_metrics", {})
        
        if system_metrics:
            console.print(f"\nSystem Resources:")
            console.print(f"  CPU: {system_metrics.get('cpu_usage', 0):.1f}%")
            console.print(f"  Memory: {system_metrics.get('memory_usage', 0):.1f}%")
            console.print(f"  Disk: {system_metrics.get('disk_usage', 0):.1f}%")
        
        # サービス状況
        services = system_status.get("services", {})
        console.print(f"\nServices: {services.get('healthy', 0)}/{services.get('total', 0)} healthy")


async def main():
    parser = argparse.ArgumentParser(description="Ai-semble v2 Operations Dashboard")
    parser.add_argument("--url", default="http://localhost:8080", 
                       help="Base URL of Ai-semble v2 orchestrator")
    parser.add_argument("--mode", choices=["dashboard", "status"], default="dashboard",
                       help="Display mode: dashboard (interactive) or status (one-time)")
    parser.add_argument("--refresh", type=int, default=5,
                       help="Refresh interval in seconds (dashboard mode)")
    
    args = parser.parse_args()
    
    async with OperationsDashboard(args.url) as dashboard:
        dashboard.refresh_interval = args.refresh
        
        if args.mode == "dashboard":
            await dashboard.run_dashboard()
        else:
            await dashboard.run_simple_status()


if __name__ == "__main__":
    try:
        # Rich library requirements check
        import rich
        asyncio.run(main())
    except ImportError:
        print("Error: 'rich' library is required for the dashboard.")
        print("Install it with: pip install rich")
        exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        exit(0)