"""
依存関係チェッカー

エージェント起動前の必要条件を確認
"""

import asyncio
import logging
import subprocess
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class DependencyChecker:
    """依存関係チェッカー"""
    
    def __init__(self):
        self.checked_dependencies: Dict[str, bool] = {}
    
    async def check_agent_dependencies(self, agent_type: str) -> Tuple[bool, str]:
        """エージェントタイプの依存関係をチェック"""
        
        if agent_type == "claude_code":
            return await self._check_claude_code_dependencies()
        elif agent_type == "openhands":
            return await self._check_openhands_dependencies()
        else:
            return False, f"未知のエージェントタイプ: {agent_type}"
    
    async def _check_claude_code_dependencies(self) -> Tuple[bool, str]:
        """ClaudeCode依存関係チェック"""
        checks = [
            ("claude_cli", self._check_claude_cli),
            ("python_version", self._check_python_version),
            ("network_access", self._check_network_access),
        ]
        
        for check_name, check_func in checks:
            success, error = await check_func()
            if not success:
                return False, f"{check_name}: {error}"
        
        return True, ""
    
    async def _check_openhands_dependencies(self) -> Tuple[bool, str]:
        """OpenHands依存関係チェック"""
        checks = [
            ("openhands_service", self._check_openhands_service),
            ("docker_access", self._check_docker_access),
            ("python_version", self._check_python_version),
        ]
        
        for check_name, check_func in checks:
            success, error = await check_func()
            if not success:
                return False, f"{check_name}: {error}"
        
        return True, ""
    
    async def _check_claude_cli(self) -> Tuple[bool, str]:
        """ClaudeCode CLI存在確認"""
        try:
            # ClaudeCode CLIの存在確認
            proc = await asyncio.create_subprocess_exec(
                "which", "claude",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            
            if proc.returncode != 0:
                return False, "ClaudeCode CLI not found in PATH"
            
            # バージョン確認
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False, f"ClaudeCode CLI error: {stderr.decode()}"
            
            version = stdout.decode().strip()
            logger.info(f"ClaudeCode CLI version: {version}")
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _check_python_version(self) -> Tuple[bool, str]:
        """Python バージョン確認"""
        try:
            import sys
            
            version = sys.version_info
            if version.major < 3 or (version.major == 3 and version.minor < 8):
                return False, f"Python 3.8+ required, found {version.major}.{version.minor}"
            
            logger.info(f"Python version: {version.major}.{version.minor}.{version.micro}")
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _check_network_access(self) -> Tuple[bool, str]:
        """ネットワークアクセス確認"""
        try:
            # 基本的なネットワーク疎通確認
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "3", "8.8.8.8",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            
            if proc.returncode != 0:
                return False, "Network connectivity issue"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _check_openhands_service(self) -> Tuple[bool, str]:
        """OpenHandsサービス確認"""
        try:
            # OpenHandsサービスの稼働確認
            # TODO: 実際のOpenHands API/サービス確認を実装
            
            # 暫定的にlocalhostの3000ポートをチェック
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            
            try:
                result = sock.connect_ex(('localhost', 3000))
                if result != 0:
                    return False, "OpenHands service not accessible on localhost:3000"
            finally:
                sock.close()
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    async def _check_docker_access(self) -> Tuple[bool, str]:
        """Docker アクセス確認"""
        try:
            # Dockerの存在とアクセス権限確認
            proc = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False, "Docker not available"
            
            # Docker daemon接続確認
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            
            if proc.returncode != 0:
                return False, "Docker daemon not accessible"
            
            version = stdout.decode().strip()
            logger.info(f"Docker version: {version}")
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def get_system_info(self) -> Dict[str, str]:
        """システム情報を取得"""
        import sys
        import platform
        
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "architecture": platform.architecture()[0],
            "hostname": platform.node(),
        }