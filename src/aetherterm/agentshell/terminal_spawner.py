"""
ターミナル生成機能

AgentShellから複数のターミナルを動的に生成する機能を提供
"""

import asyncio
import logging
import subprocess
from typing import Dict, List, Optional, Any
import uuid

log = logging.getLogger("aetherterm.agentshell.terminal_spawner")


class TerminalSpawner:
    """ターミナル生成管理クラス"""

    def __init__(self, websocket_client):
        self.websocket_client = websocket_client
        self.spawned_terminals: Dict[str, Dict[str, Any]] = {}
        self.spawn_processes: Dict[str, subprocess.Popen] = {}

    async def spawn_agent_terminal(
        self,
        agent_type: str,
        agent_id: str,
        working_directory: Optional[str] = None,
        additional_args: Optional[List[str]] = None,
    ) -> str:
        """特定のエージェント用ターミナルを生成"""
        try:
            spawn_id = str(uuid.uuid4())
            
            # 生成設定を構築
            spawn_config = {
                "spawn_id": spawn_id,
                "agent_type": agent_type,
                "agent_id": agent_id,
                "launch_mode": "agent",
                "working_directory": working_directory,
                "additional_args": additional_args or [],
            }

            # プロセス生成方式を選択
            if agent_type == "claude_code":
                await self._spawn_claude_code_terminal(spawn_config)
            elif agent_type == "openhands":
                await self._spawn_openhands_terminal(spawn_config)
            elif agent_type == "shell":
                await self._spawn_shell_terminal(spawn_config)
            else:
                raise ValueError(f"Unsupported agent type: {agent_type}")

            # 生成記録
            self.spawned_terminals[spawn_id] = spawn_config
            log.info(f"Spawned terminal for {agent_type}:{agent_id} with ID {spawn_id}")
            
            return spawn_id

        except Exception as e:
            log.error(f"Failed to spawn terminal for {agent_type}:{agent_id}: {e}")
            raise

    async def _spawn_claude_code_terminal(self, config: Dict[str, Any]):
        """ClaudeCode専用ターミナルを生成"""
        try:
            # gnome-terminal、xterm、tmuxなどを使用してターミナルを開く
            cmd = self._build_terminal_command("claude", config)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self.spawn_processes[config["spawn_id"]] = process
            log.info(f"ClaudeCode terminal process started: PID {process.pid}")

        except Exception as e:
            log.error(f"Failed to spawn ClaudeCode terminal: {e}")
            raise

    async def _spawn_openhands_terminal(self, config: Dict[str, Any]):
        """OpenHands専用ターミナルを生成"""
        try:
            # Dockerコンテナでターミナルを開く
            docker_args = [
                "docker", "run", "-it", "--rm",
                "--name", f"openhands_{config['agent_id']}",
            ]
            
            # ワークスペースをマウント
            if config.get("working_directory"):
                docker_args.extend([
                    "-v", f"{config['working_directory']}:/workspace"
                ])
            
            docker_args.append("openhands/openhands")
            
            cmd = self._build_terminal_command(docker_args, config)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self.spawn_processes[config["spawn_id"]] = process
            log.info(f"OpenHands terminal process started: PID {process.pid}")

        except Exception as e:
            log.error(f"Failed to spawn OpenHands terminal: {e}")
            raise

    async def _spawn_shell_terminal(self, config: Dict[str, Any]):
        """一般的なシェルターミナルを生成"""
        try:
            cmd = self._build_terminal_command(["/bin/bash", "-il"], config)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self.spawn_processes[config["spawn_id"]] = process
            log.info(f"Shell terminal process started: PID {process.pid}")

        except Exception as e:
            log.error(f"Failed to spawn shell terminal: {e}")
            raise

    def _build_terminal_command(self, target_cmd, config: Dict[str, Any]) -> List[str]:
        """ターミナル起動コマンドを構築"""
        terminal_title = f"Agent: {config['agent_type']}:{config['agent_id']}"
        
        # 使用可能なターミナルエミュレータを確認
        available_terminals = self._detect_available_terminals()
        
        if "gnome-terminal" in available_terminals:
            cmd = [
                "gnome-terminal",
                "--title", terminal_title,
                "--working-directory", config.get("working_directory", "/"),
                "--",
            ]
            if isinstance(target_cmd, str):
                cmd.append(target_cmd)
            else:
                cmd.extend(target_cmd)
                
        elif "xterm" in available_terminals:
            cmd = [
                "xterm",
                "-title", terminal_title,
                "-e",
            ]
            if isinstance(target_cmd, str):
                cmd.append(target_cmd)
            else:
                cmd.append(" ".join(target_cmd))
                
        elif "tmux" in available_terminals:
            # tmuxセッションを作成
            session_name = f"agent_{config['agent_id']}"
            cmd = [
                "tmux", "new-session", "-d",
                "-s", session_name,
                "-c", config.get("working_directory", "/"),
            ]
            if isinstance(target_cmd, str):
                cmd.append(target_cmd)
            else:
                cmd.append(" ".join(target_cmd))
        else:
            # フォールバック: AgentServerのWebSocket経由で通知
            cmd = ["echo", f"No suitable terminal emulator found for {terminal_title}"]
        
        return cmd

    def _detect_available_terminals(self) -> List[str]:
        """利用可能なターミナルエミュレータを検出"""
        terminals = ["gnome-terminal", "xterm", "konsole", "terminator", "tmux"]
        available = []
        
        for terminal in terminals:
            try:
                subprocess.run(
                    ["which", terminal],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                available.append(terminal)
            except subprocess.CalledProcessError:
                pass
        
        return available

    async def spawn_terminal_via_agentserver(
        self,
        agent_type: str,
        agent_id: str,
        working_directory: Optional[str] = None,
    ) -> str:
        """AgentServer経由でターミナルを生成"""
        try:
            spawn_config = {
                "agent_type": agent_type,
                "agent_id": agent_id,
                "launch_mode": "agent",
                "working_directory": working_directory,
            }

            # AgentServerにターミナル生成要求を送信
            await self.websocket_client.send_message(
                "agentserver",
                "terminal_spawn_request",
                {
                    "spawn_config": spawn_config,
                    "requester": "agentshell",
                }
            )

            log.info(f"Requested terminal spawn via AgentServer for {agent_type}:{agent_id}")
            return f"agentserver_spawn_{agent_type}_{agent_id}"

        except Exception as e:
            log.error(f"Failed to request terminal spawn via AgentServer: {e}")
            raise

    async def terminate_spawned_terminal(self, spawn_id: str) -> bool:
        """生成されたターミナルを終了"""
        try:
            if spawn_id in self.spawn_processes:
                process = self.spawn_processes[spawn_id]
                process.terminate()
                
                # 終了を待つ
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # 強制終了
                    process.kill()
                    await process.wait()
                
                del self.spawn_processes[spawn_id]
                
            if spawn_id in self.spawned_terminals:
                del self.spawned_terminals[spawn_id]
                
            log.info(f"Terminated spawned terminal: {spawn_id}")
            return True

        except Exception as e:
            log.error(f"Failed to terminate spawned terminal {spawn_id}: {e}")
            return False

    def get_spawned_terminals(self) -> Dict[str, Dict[str, Any]]:
        """生成されたターミナルの一覧を取得"""
        return self.spawned_terminals.copy()

    async def cleanup_all_spawned_terminals(self):
        """すべての生成されたターミナルをクリーンアップ"""
        spawn_ids = list(self.spawned_terminals.keys())
        
        for spawn_id in spawn_ids:
            try:
                await self.terminate_spawned_terminal(spawn_id)
            except Exception as e:
                log.error(f"Error cleaning up terminal {spawn_id}: {e}")
        
        log.info("Cleaned up all spawned terminals")