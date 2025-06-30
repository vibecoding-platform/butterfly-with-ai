"""
AgentShell対応ターミナル

AgentShellやコーディングエージェントの起動をサポートするターミナル実装
"""

import asyncio
import fcntl
import logging
import os
import pty
import signal
import subprocess
import sys
from typing import Dict, Optional, Any

from .asyncio_terminal import AsyncioTerminal

log = logging.getLogger("aetherterm.agentshell_terminal")


class AgentShellTerminal(AsyncioTerminal):
    """AgentShell対応ターミナル"""

    def __init__(
        self,
        terminal_id: str,
        socket_io,
        sid: str,
        launch_mode: str = "default",
        agent_config: Optional[Dict[str, Any]] = None,
    ):
        # 従来のコンストラクタパラメータを適応
        self.terminal_id = terminal_id
        self.socket_io = socket_io
        self.sid = sid
        self.launch_mode = launch_mode
        self.agent_config = agent_config or {}
        self.fd = None
        self.pid = None
        self.closed = False
        self.reader_task = None

        log.info(f"AgentShellTerminal created: {terminal_id}, mode: {launch_mode}")

    async def start(self):
        """ターミナルを起動"""
        try:
            if self.launch_mode == "agentshell":
                await self._start_agentshell()
            elif self.launch_mode == "agent":
                await self._start_agent()
            else:
                await self._start_default_shell()

            log.info(f"Terminal {self.terminal_id} started with mode {self.launch_mode}")

        except Exception as e:
            log.error(f"Failed to start terminal {self.terminal_id}: {e}")
            await self._emit_error(str(e))
            raise

    async def _start_agentshell(self):
        """AgentShellを起動"""
        try:
            # AgentShellの起動コマンドを構築
            cmd = [
                "uv",
                "run",
                "python",
                "-m",
                "aetherterm.agentshell.main_websocket",
                "--server",
                f"ws://localhost:57575",  # AgentServerのURL
            ]

            # エージェント設定がある場合は追加
            if "agents" in self.agent_config:
                for agent_spec in self.agent_config["agents"]:
                    cmd.extend(["-a", agent_spec])

            # その他のオプション
            if self.agent_config.get("debug", False):
                cmd.append("--debug")

            if self.agent_config.get("interactive", False):
                cmd.append("--interactive")

            if "config" in self.agent_config:
                cmd.extend(["--config", self.agent_config["config"]])

            # PTYでAgentShellを起動
            await self._start_pty_process(cmd)

            # 起動通知を送信
            await self._emit_agentshell_started()

        except Exception as e:
            log.error(f"Failed to start AgentShell: {e}")
            raise

    async def _start_agent(self):
        """特定のコーディングエージェントを起動"""
        try:
            agent_type = self.agent_config.get("agent_type", "claude_code")
            agent_id = self.agent_config.get("agent_id", "agent_001")

            if agent_type == "claude_code":
                cmd = ["claude"]
                # ClaudeCodeの追加オプション
                if "working_directory" in self.agent_config:
                    cmd.extend(["--directory", self.agent_config["working_directory"]])

            elif agent_type == "openhands":
                cmd = ["docker", "run", "-it", "--rm", "openhands/openhands"]
                # OpenHandsの追加オプション
                if "workspace" in self.agent_config:
                    cmd.extend(["-v", f"{self.agent_config['workspace']}:/workspace"])

            else:
                raise ValueError(f"Unknown agent type: {agent_type}")

            # PTYで特定エージェントを起動
            await self._start_pty_process(cmd)

            # 起動通知を送信
            await self._emit_agent_started(agent_type, agent_id)

        except Exception as e:
            log.error(f"Failed to start agent: {e}")
            raise

    async def _start_default_shell(self):
        """デフォルトシェルを起動"""
        try:
            # 通常のbashシェルを起動
            cmd = ["/bin/bash", "-il"]
            await self._start_pty_process(cmd)

        except Exception as e:
            log.error(f"Failed to start default shell: {e}")
            raise

    async def _start_pty_process(self, cmd: list):
        """PTYプロセスを起動"""
        try:
            # PTYを作成
            master_fd, slave_fd = pty.openpty()
            self.fd = master_fd

            # 環境変数を設定
            env = os.environ.copy()
            env.update({
                "TERM": "xterm-256color",
                "COLORTERM": "aetherterm",
                "AGENTSHELL_MODE": self.launch_mode,
                "AGENTSHELL_TERMINAL_ID": self.terminal_id,
            })

            # プロセスを起動
            pid = os.fork()

            if pid == 0:
                # 子プロセス
                os.close(master_fd)
                os.setsid()
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr
                os.close(slave_fd)

                # 作業ディレクトリを設定
                if "working_directory" in self.agent_config:
                    os.chdir(self.agent_config["working_directory"])

                # コマンドを実行
                os.execvpe(cmd[0], cmd, env)

            else:
                # 親プロセス
                self.pid = pid
                os.close(slave_fd)

                # ノンブロッキングに設定
                fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

                # 読み取りタスクを開始
                self.reader_task = asyncio.create_task(self._read_from_pty())

        except Exception as e:
            log.error(f"Failed to start PTY process: {e}")
            if 'master_fd' in locals():
                try:
                    os.close(master_fd)
                except:
                    pass
            if 'slave_fd' in locals():
                try:
                    os.close(slave_fd)
                except:
                    pass
            raise

    async def _read_from_pty(self):
        """PTYからデータを読み取ってクライアントに送信"""
        try:
            while not self.closed:
                try:
                    # プロセスが生きているかチェック
                    if self.pid:
                        try:
                            pid, status = os.waitpid(self.pid, os.WNOHANG)
                            if pid != 0:
                                log.info(f"Process {self.pid} exited with status {status}")
                                break
                        except OSError:
                            break

                    # PTYからデータを読み取り
                    data = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self._read_pty_data
                        ),
                        timeout=0.1,
                    )

                    if data:
                        # クライアントに送信
                        try:
                            text = data.decode("utf-8", "replace")
                            await self._emit_output(text)
                        except Exception as e:
                            log.error(f"Error decoding PTY data: {e}")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    log.error(f"Error reading from PTY: {e}")
                    break

        except Exception as e:
            log.error(f"PTY reader task error: {e}")
        finally:
            await self.stop()

    def _read_pty_data(self):
        """PTYからデータを読み取り（ブロッキング操作）"""
        try:
            return os.read(self.fd, 4096)
        except OSError:
            return b""

    async def write_input(self, input_data: str):
        """ターミナルに入力を書き込み"""
        if self.closed or not self.fd:
            return

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, os.write, self.fd, input_data.encode("utf-8")
            )
        except Exception as e:
            log.error(f"Error writing to PTY: {e}")
            await self.stop()

    async def resize(self, rows: int, cols: int):
        """ターミナルサイズを変更"""
        if self.closed or not self.fd:
            return

        try:
            import struct
            import termios
            s = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, s)
        except Exception as e:
            log.error(f"Error resizing PTY: {e}")

    async def stop(self):
        """ターミナルを停止"""
        if self.closed:
            return

        self.closed = True
        log.info(f"Stopping terminal {self.terminal_id}")

        # 読み取りタスクをキャンセル
        if self.reader_task and not self.reader_task.done():
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass

        # PTYを閉じる
        if self.fd is not None:
            try:
                os.close(self.fd)
            except Exception as e:
                log.debug(f"Error closing PTY fd: {e}")

        # プロセスを終了
        if self.pid:
            try:
                # まずSIGTERMを送信
                os.kill(self.pid, signal.SIGTERM)

                # 終了を待つ
                for _ in range(50):
                    try:
                        pid, status = os.waitpid(self.pid, os.WNOHANG)
                        if pid != 0:
                            break
                    except OSError:
                        break
                    await asyncio.sleep(0.1)
                else:
                    # 強制終了
                    try:
                        os.kill(self.pid, signal.SIGKILL)
                        os.waitpid(self.pid, 0)
                    except OSError:
                        pass

            except Exception as e:
                log.error(f"Error terminating process: {e}")

        # 終了通知を送信
        await self._emit_closed()

    async def _emit_output(self, output: str):
        """出力をクライアントに送信"""
        try:
            await self.socket_io.emit(
                "terminal_output",
                {
                    "terminal_id": self.terminal_id,
                    "output": output,
                },
                room=self.sid,
            )
        except Exception as e:
            log.error(f"Error emitting output: {e}")

    async def _emit_agentshell_started(self):
        """AgentShell起動通知を送信"""
        try:
            await self.socket_io.emit(
                "agentshell_started",
                {
                    "terminal_id": self.terminal_id,
                    "launch_mode": self.launch_mode,
                    "agent_config": self.agent_config,
                },
                room=self.sid,
            )
        except Exception as e:
            log.error(f"Error emitting agentshell started: {e}")

    async def _emit_agent_started(self, agent_type: str, agent_id: str):
        """エージェント起動通知を送信"""
        try:
            await self.socket_io.emit(
                "agent_started",
                {
                    "terminal_id": self.terminal_id,
                    "agent_type": agent_type,
                    "agent_id": agent_id,
                    "launch_mode": self.launch_mode,
                },
                room=self.sid,
            )
        except Exception as e:
            log.error(f"Error emitting agent started: {e}")

    async def _emit_closed(self):
        """終了通知を送信"""
        try:
            await self.socket_io.emit(
                "terminal_closed",
                {"terminal_id": self.terminal_id},
                room=self.sid,
            )
        except Exception as e:
            log.error(f"Error emitting closed: {e}")

    async def _emit_error(self, error_message: str):
        """エラー通知を送信"""
        try:
            await self.socket_io.emit(
                "terminal_error",
                {
                    "terminal_id": self.terminal_id,
                    "error": error_message,
                },
                room=self.sid,
            )
        except Exception as e:
            log.error(f"Error emitting error: {e}")

    async def spawn_additional_terminal(self, spawn_config: Dict[str, Any]) -> str:
        """追加のターミナルを生成（AgentShellから他のターミナルを開く）"""
        try:
            new_terminal_id = f"{self.terminal_id}_spawn_{spawn_config.get('agent_type', 'default')}"
            
            # 新しいターミナルを作成
            new_terminal = AgentShellTerminal(
                terminal_id=new_terminal_id,
                socket_io=self.socket_io,
                sid=self.sid,
                launch_mode=spawn_config.get("launch_mode", "agent"),
                agent_config=spawn_config,
            )

            # 新しいターミナルを起動
            await new_terminal.start()

            # 生成通知を送信
            await self.socket_io.emit(
                "terminal_spawned",
                {
                    "parent_terminal_id": self.terminal_id,
                    "new_terminal_id": new_terminal_id,
                    "spawn_config": spawn_config,
                },
                room=self.sid,
            )

            log.info(f"Spawned new terminal {new_terminal_id} from {self.terminal_id}")
            return new_terminal_id

        except Exception as e:
            log.error(f"Failed to spawn additional terminal: {e}")
            await self._emit_error(f"Failed to spawn terminal: {e}")
            raise