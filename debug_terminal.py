#!/usr/bin/env python3
"""
Terminal Display Debug Script
Continuously monitor and debug terminal display issues
"""

import time
import asyncio
import subprocess
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('terminal_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TerminalDebugger:
    def __init__(self):
        self.frontend_dir = Path("frontend")
        self.static_dir = Path("static")
        self.build_interval = 30  # seconds
        self.last_build = 0
        self.debug_checks = [
            self.check_frontend_files,
            self.check_static_files,
            self.check_server_status,
            self.check_socket_connections,
            self.monitor_logs
        ]
    
    async def run_continuous_debug(self):
        """Run debugging checks continuously"""
        logger.info("🔍 Starting continuous terminal debugging...")
        iteration = 0
        
        while True:
            try:
                iteration += 1
                logger.info(f"🔄 Debug iteration #{iteration}")
                
                # Check if frontend needs rebuilding
                await self.check_and_rebuild_frontend()
                
                # Run all debug checks
                for check in self.debug_checks:
                    try:
                        await check()
                    except Exception as e:
                        logger.error(f"❌ Check {check.__name__} failed: {e}")
                
                # Wait before next iteration
                logger.info(f"⏳ Waiting 60 seconds before next check...")
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Debugging stopped by user")
                break
            except Exception as e:
                logger.error(f"💥 Unexpected error in debug loop: {e}")
                await asyncio.sleep(10)
    
    async def check_and_rebuild_frontend(self):
        """Check if frontend needs rebuilding and rebuild if necessary"""
        current_time = time.time()
        
        # Check if src files are newer than last build
        src_files_changed = False
        if self.frontend_dir.exists():
            for src_file in (self.frontend_dir / "src").rglob("*.*"):
                if src_file.stat().st_mtime > self.last_build:
                    src_files_changed = True
                    break
        
        if src_files_changed or (current_time - self.last_build) > 300:  # 5 minutes
            logger.info("🔧 Rebuilding frontend...")
            try:
                result = subprocess.run(
                    ["pnpm", "build"],
                    cwd=self.frontend_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    logger.info("✅ Frontend build successful")
                    # Copy to static
                    subprocess.run(
                        ["cp", "-r", "dist/*", "../static/"],
                        cwd=self.frontend_dir,
                        shell=True
                    )
                    self.last_build = current_time
                else:
                    logger.error(f"❌ Frontend build failed: {result.stderr}")
                    
            except Exception as e:
                logger.error(f"💥 Frontend build error: {e}")
    
    async def check_frontend_files(self):
        """Check frontend file integrity"""
        logger.info("📁 Checking frontend files...")
        
        if not self.frontend_dir.exists():
            logger.error("❌ Frontend directory not found")
            return
        
        key_files = [
            "src/components/terminal/TerminalTab.vue",
            "src/stores/aetherTerminalServiceStore.ts",
            "src/stores/terminalTabStore.ts",
            "dist/index.html"
        ]
        
        for file_path in key_files:
            full_path = self.frontend_dir / file_path
            if full_path.exists():
                logger.info(f"✅ {file_path} exists")
            else:
                logger.error(f"❌ {file_path} missing")
    
    async def check_static_files(self):
        """Check static file deployment"""
        logger.info("📦 Checking static files...")
        
        if not self.static_dir.exists():
            logger.error("❌ Static directory not found")
            return
        
        key_files = ["index.html", "assets"]
        for file_name in key_files:
            file_path = self.static_dir / file_name
            if file_path.exists():
                logger.info(f"✅ Static {file_name} exists")
            else:
                logger.error(f"❌ Static {file_name} missing")
    
    async def check_server_status(self):
        """Check server health"""
        logger.info("🌐 Checking server status...")
        
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:57575/health"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ Server responding to health check")
            else:
                logger.error("❌ Server health check failed")
                
        except Exception as e:
            logger.error(f"💥 Server check error: {e}")
    
    async def check_socket_connections(self):
        """Check socket.io connections"""
        logger.info("🔌 Checking socket connections...")
        
        try:
            result = subprocess.run(
                ["ss", "-tulpn", "|", "grep", "57575"],
                shell=True,
                capture_output=True,
                text=True
            )
            
            if "57575" in result.stdout:
                logger.info("✅ Socket port 57575 is listening")
            else:
                logger.error("❌ Socket port 57575 not found")
                
        except Exception as e:
            logger.error(f"💥 Socket check error: {e}")
    
    async def monitor_logs(self):
        """Monitor recent log entries for errors"""
        logger.info("📋 Monitoring logs...")
        
        try:
            # Check for recent errors in supervisor logs
            result = subprocess.run(
                ["tail", "-n", "20", "/var/log/supervisor/agentserver.log"],
                capture_output=True,
                text=True
            )
            
            if "ERROR" in result.stdout or "CRITICAL" in result.stdout:
                logger.warning("⚠️ Found errors in server logs")
                for line in result.stdout.split('\n'):
                    if "ERROR" in line or "CRITICAL" in line:
                        logger.warning(f"📋 {line}")
            else:
                logger.info("✅ No recent errors in server logs")
                
        except Exception as e:
            logger.error(f"💥 Log monitoring error: {e}")

async def main():
    """Main function"""
    debugger = TerminalDebugger()
    await debugger.run_continuous_debug()

if __name__ == "__main__":
    asyncio.run(main())