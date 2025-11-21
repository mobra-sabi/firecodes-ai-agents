#!/usr/bin/env python3
"""
📊 DEDEMAN LIVE MONITOR
Real-time progress monitoring
"""

import time
import os
import subprocess
from datetime import datetime

def monitor_live():
    """Monitor Dedeman agent creation live"""
    
    log_file = "/tmp/dedeman_playwright.log"
    start_time = time.time()
    
    print("=" * 80)
    print("📊 DEDEMAN AGENT - LIVE MONITOR")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Log: {log_file}")
    print("=" * 80)
    print("")
    
    last_size = 0
    
    try:
        while True:
            # Check if process still running
            result = subprocess.run(
                ['pgrep', '-f', 'playwright_agent_creator.py'],
                capture_output=True
            )
            
            if result.returncode != 0:
                print("\n⚠️ Process finished or not found")
                break
            
            # Check file size
            if os.path.exists(log_file):
                current_size = os.path.getsize(log_file)
                
                if current_size > last_size:
                    # Read new content
                    with open(log_file, 'r') as f:
                        f.seek(last_size)
                        new_content = f.read()
                        
                        if new_content:
                            print(new_content, end='', flush=True)
                    
                    last_size = current_size
            
            # Elapsed time
            elapsed = time.time() - start_time
            print(f"\r⏱️ Elapsed: {elapsed/60:.1f} min", end='', flush=True)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped (process still running in background)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    monitor_live()

