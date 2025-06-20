"""
AetherTerm AgentShell - 同期PTYモード

test.pyで実装された同期PTY機能を使用した
シェル監視とAI連携のエントリーポイント
"""

import asyncio
import logging
import sys
from typing import List, Optional

import click

from .config import WrapperConfig
from .observability import setup_telemetry
from .pty import default_async_log, run_shell_with_async_backend
from .service.ai_service import AIService

logger = logging.getLogger(__name__)


async def ai_enhanced_log(message: str, ai_service: Optional[AIService] = None) -> None:
    """
    AI機能を統合した非同期ログ処理

    Args:
        message: ログメッセージ
        ai_service: AIサービス（オプション）
    """
    logger.info(f"[AI LOG] 処理中: '{message[:50]}...'")

    # AI分析を実行（オプション）
    if ai_service:
        try:
            # AIにメッセージを分析させる
            analysis = await ai_service.analyze_terminal_output(message)
            if analysis:
                logger.info(f"[AI ANALYSIS] {analysis}")
        except Exception as e:
            logger.warning(f"AI分析エラー: {e}")

    # 実際のログ処理をシミュレート
    await asyncio.sleep(0.5)
    logger.info(f"[AI LOG] 完了: '{message[:50]}...'")


@click.command()
@click.option("-c", "--config", type=click.Path(exists=True), help="設定ファイルのパス")
@click.option("-d", "--debug", is_flag=True, help="デバッグモードを有効にする")
@click.option("--shell", type=str, help="実行するシェルコマンド")
@click.option("--keywords", type=str, help="監視するキーワード（カンマ区切り）")
@click.option("--session-id", type=str, default="sync-shell", help="セッションID")
@click.option("--enable-ai", is_flag=True, help="AI機能を有効にする")
@click.option(
    "--ai-provider",
    type=click.Choice(["openai", "anthropic", "local"]),
    default="openai",
    help="AIプロバイダー",
)
def main(
    config: Optional[str],
    debug: bool,
    shell: Optional[str],
    keywords: Optional[str],
    session_id: str,
    enable_ai: bool,
    ai_provider: str,
) -> None:
    """
    AetherTerm AgentShell - 同期PTYモード

    test.pyで実装された同期PTY機能を使用して、
    シェル監視とAI連携を提供します。

    使用例:

    基本的な使用:
    aetherterm-shell-sync

    キーワード監視:
    aetherterm-shell-sync --keywords "error,warning,fail,exception"

    AI機能付き:
    aetherterm-shell-sync --enable-ai --ai-provider openai
    """
    # ログレベル設定
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("AetherTerm AgentShell (同期PTYモード) を開始します")

    try:
        # 設定を読み込み
        if config:
            wrapper_config = WrapperConfig.from_file(config)
        else:
            wrapper_config = WrapperConfig()

        # テレメトリーを設定
        telemetry_manager = setup_telemetry(
            service_name="aetherterm-agentshell-sync",
            environment="development" if debug else "production",
            enable_console_export=debug,
        )

        # キーワードリストを準備
        keywords_to_monitor: Optional[List[str]] = None
        if keywords:
            keywords_to_monitor = [k.strip() for k in keywords.split(",")]

        # AI機能を設定
        ai_service: Optional[AIService] = None
        async_log_callback = default_async_log

        if enable_ai:
            try:
                # AI設定を準備
                ai_config = {
                    "provider": ai_provider,
                    "api_key": wrapper_config.ai_api_key
                    if hasattr(wrapper_config, "ai_api_key")
                    else None,
                }

                # AIサービスを初期化
                ai_service = AIService(ai_config)

                # AI機能付きログコールバックを設定
                async_log_callback = lambda msg: ai_enhanced_log(msg, ai_service)

                logger.info(f"AI機能を有効にしました: {ai_provider}")

            except Exception as e:
                logger.warning(f"AI機能の初期化に失敗しました: {e}")
                logger.info("AI機能なしで続行します")

        # 同期PTYシェルを実行
        run_shell_with_async_backend(
            session_id=session_id,
            keywords_to_monitor=keywords_to_monitor,
            shell_command=shell,
            async_log_callback=async_log_callback,
        )

    except KeyboardInterrupt:
        logger.info("ユーザーによって中断されました")
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        if debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("AetherTerm AgentShell (同期PTYモード) を終了します")


if __name__ == "__main__":
    main()
