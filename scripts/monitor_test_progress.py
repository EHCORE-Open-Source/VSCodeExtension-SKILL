#!/usr/bin/env python3
"""
Test Progress Monitor

Monitors the progress of consistency testing in real-time.

Usage:
    python3 monitor_test_progress.py --dir test_pages_594_601 --expected-runs 3
    python3 monitor_test_progress.py --dir test_pages_202_204 --expected-runs 10 --interval 30

Author: Claude Code
Date: 2025-10-12
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class TestProgressMonitor:
    """
    Monitor test progress by checking output directories
    """

    def __init__(self, test_dir: str, expected_runs: int, interval: int = 30):
        """
        Initialize monitor

        Args:
            test_dir: Test output directory to monitor
            expected_runs: Expected number of test runs
            interval: Monitoring interval in seconds
        """
        self.test_dir = Path(test_dir)
        self.expected_runs = expected_runs
        self.interval = interval
        self.last_status = None

    def get_run_dirs(self) -> List[Path]:
        """Get all run directories"""
        if not self.test_dir.exists():
            return []
        return sorted(self.test_dir.glob("run_*"))

    def analyze_run(self, run_dir: Path) -> Optional[Dict]:
        """
        Analyze a single run directory

        Args:
            run_dir: Run directory path

        Returns:
            Run status dictionary or None if incomplete
        """
        json_files = list(run_dir.glob("*.json"))

        if not json_files:
            return {
                "status": "running",
                "complete": False,
                "run_dir": run_dir.name,
                "timestamp": run_dir.stat().st_mtime
            }

        # Run completed - parse JSON
        json_file = json_files[0]

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            functions = data.get('functions', [])

            return {
                "status": "completed",
                "complete": True,
                "run_dir": run_dir.name,
                "json_file": json_file.name,
                "function_count": len(functions),
                "functions": [
                    {
                        "name": f.get('function_name'),
                        "pages": f"{f.get('sources', {}).get('start_page')}-{f.get('sources', {}).get('end_page')}"
                    }
                    for f in functions
                ],
                "timestamp": run_dir.stat().st_mtime,
                "file_size": json_file.stat().st_size
            }
        except Exception as e:
            return {
                "status": "error",
                "complete": False,
                "run_dir": run_dir.name,
                "error": str(e),
                "timestamp": run_dir.stat().st_mtime
            }

    def get_current_status(self) -> Dict:
        """
        Get current test status

        Returns:
            Status dictionary
        """
        run_dirs = self.get_run_dirs()
        completed_runs = []
        running_runs = []
        error_runs = []

        for run_dir in run_dirs:
            run_info = self.analyze_run(run_dir)
            if run_info:
                if run_info['status'] == 'completed':
                    completed_runs.append(run_info)
                elif run_info['status'] == 'error':
                    error_runs.append(run_info)
                else:
                    running_runs.append(run_info)

        total_runs = len(run_dirs)
        completed_count = len(completed_runs)
        progress = (completed_count / self.expected_runs * 100) if self.expected_runs > 0 else 0

        return {
            "total_runs": total_runs,
            "completed_count": completed_count,
            "running_count": len(running_runs),
            "error_count": len(error_runs),
            "expected_runs": self.expected_runs,
            "progress": progress,
            "completed_runs": completed_runs,
            "running_runs": running_runs,
            "error_runs": error_runs,
            "timestamp": datetime.now()
        }

    def print_status(self, status: Dict):
        """
        Print status to console

        Args:
            status: Status dictionary
        """
        # Clear screen (works on Unix and Windows)
        os.system('clear' if os.name == 'posix' else 'cls')

        print("="*80)
        print(f"📊 Test Progress Monitor - {self.test_dir.name}")
        print(f"⏰ Updated: {status['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        print()

        # Progress bar
        progress = status['progress']
        completed = status['completed_count']
        expected = status['expected_runs']

        bar_length = 40
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(f"Progress: [{bar}] {progress:.1f}%")
        print(f"Completed: {completed}/{expected} runs")
        print()

        # Summary
        print("-"*80)
        print("📈 Summary:")
        print(f"  ✅ Completed: {status['completed_count']}")
        print(f"  🔄 Running:   {status['running_count']}")
        print(f"  ❌ Errors:    {status['error_count']}")
        print(f"  📊 Total:     {status['total_runs']}")
        print("-"*80)
        print()

        # Completed runs
        if status['completed_runs']:
            print("✅ Completed Runs:")
            for run in status['completed_runs']:
                print(f"  • {run['run_dir']} - {run['function_count']} function(s)")
                for func in run['functions']:
                    print(f"    - {func['name']} (pages {func['pages']})")
            print()

        # Running runs
        if status['running_runs']:
            print("🔄 Running Runs:")
            for run in status['running_runs']:
                elapsed = time.time() - run['timestamp']
                print(f"  • {run['run_dir']} - Running ({elapsed:.0f}s elapsed)")
            print()

        # Errors
        if status['error_runs']:
            print("❌ Error Runs:")
            for run in status['error_runs']:
                print(f"  • {run['run_dir']} - Error: {run['error']}")
            print()

        # Check for consistency
        if len(status['completed_runs']) > 1:
            signatures = set()
            for run in status['completed_runs']:
                sig = tuple((f['name'], f['pages']) for f in run['functions'])
                signatures.add(sig)

            if len(signatures) == 1:
                print("✅ All completed runs are CONSISTENT")
            else:
                print("⚠️ INCONSISTENCY detected in completed runs!")
                print(f"   Found {len(signatures)} different results")
            print()

        # Footer
        print("-"*80)
        if progress < 100:
            print(f"⏳ Waiting for completion... (checking every {self.interval}s)")
            print("Press Ctrl+C to stop monitoring")
        else:
            print("✅ All tests completed!")
        print("-"*80)

    def monitor(self):
        """
        Main monitoring loop
        """
        print(f"🔍 Starting monitor for: {self.test_dir}")
        print(f"   Expected runs: {self.expected_runs}")
        print(f"   Check interval: {self.interval}s")
        print()

        try:
            while True:
                status = self.get_current_status()
                self.print_status(status)

                # Check if completed
                if status['completed_count'] >= self.expected_runs:
                    print("\n🎉 All expected runs completed!")

                    # Check consistency
                    if len(set(
                        tuple((f['name'], f['pages']) for f in run['functions'])
                        for run in status['completed_runs']
                    )) == 1:
                        print("✅ All runs are consistent!")
                        return 0
                    else:
                        print("⚠️ Inconsistencies detected!")
                        return 1

                self.last_status = status
                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\n⚠️ Monitoring stopped by user")
            return 2

def main():
    parser = argparse.ArgumentParser(
        description="Monitor test progress in real-time",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--dir', required=True,
                       help='Test output directory to monitor')

    parser.add_argument('--expected-runs', type=int, required=True,
                       help='Expected number of test runs')

    parser.add_argument('--interval', type=int, default=30,
                       help='Monitoring interval in seconds (default: 30)')

    args = parser.parse_args()

    monitor = TestProgressMonitor(
        test_dir=args.dir,
        expected_runs=args.expected_runs,
        interval=args.interval
    )

    return monitor.monitor()

if __name__ == '__main__':
    sys.exit(main())
