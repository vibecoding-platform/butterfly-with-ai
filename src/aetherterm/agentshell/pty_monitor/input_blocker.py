"""
Input Blocker

危険検出時のユーザー入力ブロック機能
Ctrl+D検出による解除機能を含む
"""

import logging
import select
import sys
import termios
import threading
import tty
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class BlockState(Enum):
    """ブロック状態"""

    NORMAL = "normal"
    BLOCKED = "blocked"
    WAITING_CONFIRMATION = "waiting_confirmation"


class InputBlocker:
    """入力制御クラス"""

    def __init__(self):
        """初期化"""
        self.state = BlockState.NORMAL
        self.original_settings = None
        self.input_thread = None
        self.running = False
        self.unblock_callback: Optional[Callable[[], None]] = None
        self._lock = threading.Lock()

    def set_unblock_callback(self, callback: Callable[[], None]):
        """
        ブロック解除時のコールバック関数を設定

        Args:
            callback: ブロック解除時に呼び出される関数
        """
        self.unblock_callback = callback

    def start_monitoring(self):
        """入力監視を開始"""
        if self.running:
            logger.warning("Input monitoring is already running")
            return

        try:
            # 元の端末設定を保存
            self.original_settings = termios.tcgetattr(sys.stdin)

            self.running = True

            # 入力監視スレッド開始
            self.input_thread = threading.Thread(target=self._input_monitor_loop)
            self.input_thread.daemon = True
            self.input_thread.start()

            logger.info("Started input monitoring")

        except Exception as e:
            logger.error(f"Failed to start input monitoring: {e}")
            raise

    def stop_monitoring(self):
        """入力監視を停止"""
        self.running = False

        # 元の端末設定を復元
        if self.original_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
            except Exception as e:
                logger.error(f"Failed to restore terminal settings: {e}")
            finally:
                self.original_settings = None

        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=2)

        logger.info("Stopped input monitoring")

    def block_input(self, reason: str = "危険なコマンドが検出されました"):
        """
        入力をブロック

        Args:
            reason: ブロック理由
        """
        with self._lock:
            if self.state == BlockState.NORMAL:
                self.state = BlockState.BLOCKED
                self._display_block_message(reason)
                logger.warning(f"Input blocked: {reason}")

    def unblock_input(self):
        """入力ブロックを解除"""
        with self._lock:
            if self.state in [BlockState.BLOCKED, BlockState.WAITING_CONFIRMATION]:
                self.state = BlockState.NORMAL
                self._display_unblock_message()
                logger.info("Input unblocked")

                if self.unblock_callback:
                    try:
                        self.unblock_callback()
                    except Exception as e:
                        logger.error(f"Error in unblock callback: {e}")

    def is_blocked(self) -> bool:
        """入力がブロックされているかどうかを返す"""
        return self.state != BlockState.NORMAL

    def _input_monitor_loop(self):
        """入力監視ループ（別スレッドで実行）"""
        while self.running:
            try:
                # 標準入力からの入力を監視
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    # 入力がある場合
                    if self.state == BlockState.BLOCKED:
                        # ブロック中の場合、入力を読み取って処理
                        self._handle_blocked_input()
                    elif self.state == BlockState.WAITING_CONFIRMATION:
                        # 確認待ち中の場合、Ctrl+Dを待機
                        self._handle_confirmation_input()

            except Exception as e:
                if self.running:
                    logger.error(f"Error in input monitor loop: {e}")
                break

    def _handle_blocked_input(self):
        """ブロック中の入力処理"""
        try:
            # 非正規モードで1文字読み取り
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)

            # Ctrl+D (ASCII 4) の検出
            if ord(char) == 4:  # Ctrl+D
                with self._lock:
                    self.state = BlockState.WAITING_CONFIRMATION
                    self._display_confirmation_message()
            else:
                # その他の入力は無視（ブロック中のため）
                self._display_block_reminder()

        except Exception as e:
            logger.error(f"Error handling blocked input: {e}")
        finally:
            # 端末設定を復元
            if self.original_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
                except Exception:
                    pass

    def _handle_confirmation_input(self):
        """確認待ち中の入力処理"""
        try:
            # 非正規モードで1文字読み取り
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)

            # Ctrl+D (ASCII 4) の再検出で解除
            if ord(char) == 4:  # Ctrl+D
                self.unblock_input()
            else:
                # その他の入力でブロック状態に戻る
                with self._lock:
                    self.state = BlockState.BLOCKED
                    self._display_block_message("確認がキャンセルされました")

        except Exception as e:
            logger.error(f"Error handling confirmation input: {e}")
        finally:
            # 端末設定を復元
            if self.original_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
                except Exception:
                    pass

    def _display_block_message(self, reason: str):
        """ブロックメッセージを表示"""
        message = f"""
\033[1;31m
╔══════════════════════════════════════════════════════════════╗
║                    ⚠️  CRITICAL ALERT ⚠️                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  {reason:<58} ║
║                                                              ║
║  入力がブロックされました。                                    ║
║  続行するには Ctrl+D を押してください。                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
\033[0m
"""
        print(message, flush=True)

    def _display_confirmation_message(self):
        """確認メッセージを表示"""
        message = """
\033[1;33m
╔══════════════════════════════════════════════════════════════╗
║                      🔓 確認が必要です                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  本当に続行しますか？                                          ║
║                                                              ║
║  続行する場合: もう一度 Ctrl+D を押してください                 ║
║  キャンセル:   他のキーを押してください                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
\033[0m
"""
        print(message, flush=True)

    def _display_unblock_message(self):
        """ブロック解除メッセージを表示"""
        message = """
\033[1;32m
╔══════════════════════════════════════════════════════════════╗
║                    ✅ ブロック解除                            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  入力ブロックが解除されました。                                ║
║  通常の操作を続行できます。                                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
\033[0m
"""
        print(message, flush=True)

    def _display_block_reminder(self):
        """ブロック中のリマインダーメッセージを表示"""
        message = (
            "\033[1;31m⚠️  入力がブロックされています。Ctrl+D を押して確認してください。\033[0m"
        )
        print(message, flush=True)

    def __enter__(self):
        """コンテキストマネージャー対応"""
        self.start_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー対応"""
        self.stop_monitoring()
