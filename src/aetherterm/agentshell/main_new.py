"""
AetherTerm Shell - 独立したAIシェルシステム

直接AIプロバイダーと通信し、AetherTermサーバーに依存しない
独立したAI機能を提供します。サーバー連携はオプショナルです。
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import click

from .config import WrapperConfig
from .observability import setup_telemetry
from .service.shell_agent import AetherTermShellAgent

logger = logging.getLogger(__name__)


class AetherTermShell:
    """
    AetherTerm Shell - 独立したAIシェルシステム

    AIプロバイダーと直接通信し、サーバーに依存しない
    AI機能を提供します。サーバー連携はオプショナルです。
    """

    def __init__(self, config: WrapperConfig):
        self.config = config
        self._shell_agent: Optional[AetherTermShellAgent] = None
        self._is_running = False
        self._shell_process = None
        self._current_session_id: Optional[str] = None

    async def start(self) -> None:
        """AetherTerm Shellを開始"""
        if self._is_running:
            return

        logger.info(f"AetherTerm Shell を開始します（モード: {self.config.mode}）")

        try:
            # 設定を適用
            self.config.setup_logging()
            self.config.apply_environment_overrides()

            # テレメトリーを設定
            if self.config.telemetry.enable_tracing:
                setup_telemetry(self.config.telemetry)

            # Shell Agentを初期化
            self._shell_agent = AetherTermShellAgent(self.config)
            await self._shell_agent.start()

            self._is_running = True

            # 動作モードに応じた情報表示
            self._display_startup_info()

            # シェルを起動
            await self._start_shell()

            logger.info("AetherTerm Shell が開始されました")

        except Exception as e:
            logger.error(f"AetherTerm Shell の開始に失敗しました: {e}")
            raise

    async def stop(self) -> None:
        """AetherTerm Shellを停止"""
        if not self._is_running:
            return

        logger.info("AetherTerm Shell を停止します")

        try:
            # シェルプロセスを終了
            if self._shell_process:
                self._shell_process.terminate()
                try:
                    await asyncio.wait_for(self._shell_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._shell_process.kill()
                    await self._shell_process.wait()

            # Shell Agentを停止
            if self._shell_agent:
                await self._shell_agent.stop()

            self._is_running = False
            logger.info("AetherTerm Shell が停止されました")

        except Exception as e:
            logger.error(f"AetherTerm Shell の停止中にエラーが発生しました: {e}")

    def _display_startup_info(self) -> None:
        """起動時の情報を表示"""
        if not self._shell_agent:
            return

        status = self._shell_agent.get_status()
        mode = status["operation_mode"]

        print("=" * 60)
        print("🚀 AetherTerm Shell - 独立したAIシェルシステム")
        print("=" * 60)

        if mode == "connected":
            print("📡 動作モード: 連携モード（AI + サーバー）")
            server_status = status.get("server_connector", {})
            print(
                f"🔗 サーバー接続: {'✅ 接続済み' if server_status.get('connected') else '❌ 未接続'}"
            )
        elif mode == "standalone_with_ai":
            print("🤖 動作モード: スタンドアロンモード（AIのみ）")
            print(f"🧠 AIプロバイダー: {status['ai_service']['provider_type']}")
        else:
            print("📝 動作モード: ローカルモード（AI機能なし）")

        print(f"⚙️  AI機能: {'✅ 有効' if status['ai_service']['has_ai_provider'] else '❌ 無効'}")
        print(f"🐛 デバッグ: {'✅ 有効' if status['config']['debug'] else '❌ 無効'}")
        print("=" * 60)
        print()

    async def _start_shell(self) -> None:
        """Bashシェルを起動"""
        try:
            # 環境変数を設定
            env = os.environ.copy()
            env["AETHERTERM_WRAPPER"] = "1"
            env["AETHERTERM_MODE"] = self.config.mode

            # セッションを作成
            if self._shell_agent:
                # 仮のPIDでセッションを作成（実際のPIDは後で更新）
                self._current_session_id = self._shell_agent.create_session(
                    shell_pid=0,  # 後で更新
                    terminal_size=(24, 80),
                    metadata={"mode": self.config.mode},
                )
                env["AETHERTERM_SESSION_ID"] = self._current_session_id

            # Bashを起動
            self._shell_process = await asyncio.create_subprocess_exec(
                "/bin/bash",
                "--login",
                "-i",
                env=env,
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            logger.info(f"Bashシェルを起動しました (PID: {self._shell_process.pid})")

            # セッションのPIDを更新
            if self._shell_agent and self._current_session_id:
                self._shell_agent.update_session(
                    self._current_session_id,
                    metadata={"shell_pid": self._shell_process.pid},
                )

            # シェルの終了を待機
            await self._shell_process.wait()

            logger.info("Bashシェルが終了しました")

            # セッションを削除
            if self._shell_agent and self._current_session_id:
                self._shell_agent.remove_session(self._current_session_id)

        except Exception as e:
            logger.error(f"Bashシェルの起動に失敗しました: {e}")
            raise

    def is_running(self) -> bool:
        """AetherTerm Shellが実行中かどうかを確認"""
        return self._is_running

    def get_status(self) -> dict:
        """現在の状態を取得"""
        if self._shell_agent:
            return self._shell_agent.get_status()
        return {"is_running": self._is_running}


@click.command()
@click.option(
    "--config", "-c", type=click.Path(exists=True, path_type=Path), help="設定ファイルのパス"
)
@click.option("--mode", "-m", type=click.Choice(["standalone", "connected"]), help="動作モード")
@click.option(
    "--ai-provider", type=click.Choice(["openai", "anthropic", "local"]), help="AIプロバイダー"
)
@click.option("--debug", "-d", is_flag=True, help="デバッグモードを有効にする")
@click.option("--server-url", help="AetherTermサーバーのURL")
@click.option("--api-key", help="AI APIキー")
def cli_main(
    config: Optional[Path],
    mode: Optional[str],
    ai_provider: Optional[str],
    debug: bool,
    server_url: Optional[str],
    api_key: Optional[str],
) -> None:
    """
    AetherTerm Shell - 独立したAIシェルシステム

    直接AIプロバイダーと通信し、AetherTermサーバーに依存しない
    独立したAI機能を提供します。サーバー連携はオプショナルです。

    使用例:

    スタンドアロンモード（AIのみ）:
    aetherterm-shell --mode standalone --ai-provider openai

    連携モード（AI + サーバー）:
    aetherterm-shell --mode connected --server-url http://localhost:57575

    設定ファイル使用:
    aetherterm-shell --config standalone.toml
    """
    # 設定を読み込み
    if config:
        wrapper_config = WrapperConfig.load_from_file(config)
    else:
        wrapper_config = WrapperConfig()

    # コマンドライン引数で設定を上書き
    if mode:
        wrapper_config.mode = mode
    if ai_provider:
        wrapper_config.ai_service.provider = ai_provider
    if debug:
        wrapper_config.debug = debug
    if server_url:
        wrapper_config.server_connection.server_url = server_url
        wrapper_config.server_connection.enabled = True
    if api_key:
        wrapper_config.ai_service.api_key = api_key

    # 環境変数による上書きを適用
    wrapper_config.apply_environment_overrides()

    # ログレベルを設定
    log_level = logging.DEBUG if wrapper_config.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # メインプログラムを実行
    shell = AetherTermShell(wrapper_config)

    # シグナルハンドラーを設定
    def signal_handler(signum, frame):
        logger.info(f"シグナル {signum} を受信しました")
        asyncio.create_task(shell.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(shell.start())
    except KeyboardInterrupt:
        logger.info("プログラムが中断されました")
    except Exception as e:
        logger.error(f"プログラムの実行に失敗しました: {e}")
        sys.exit(1)


def main() -> None:
    """メイン関数（スクリプトエントリーポイント用）"""
    cli_main()


if __name__ == "__main__":
    main()
