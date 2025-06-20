import asyncio
import errno  # ★追加しました！
import fcntl
import os
import pty
import queue
import select
import signal
import struct
import sys
import termios
import threading
import tty


# --- 同期PTYシェルのユーティリティ関数 ---
def set_raw_mode(fd):
    """ファイルディスクリプタをRAWモードに設定する"""
    try:
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
        return old_settings
    except termios.error as e:
        sys.stderr.write(f"Error setting raw mode: {e}\n")
        return None


def restore_terminal_mode(fd, settings):
    """ターミナルモードを元に戻す"""
    if settings:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, settings)
        except termios.error as e:
            sys.stderr.write(f"Error restoring terminal mode for fd {fd}: {e}\n")


# --- 非同期ロギング関数 ---
async def async_log(message):
    """
    非同期でログメッセージを処理するコルーチン。
    ここでは単に数秒待って表示するだけだが、実際にはファイルI/OやネットワークI/Oを含む。
    """
    print(f"[ASYNC LOG] Processing log: '{message[:50]}...' (simulated work)", file=sys.stderr)
    await asyncio.sleep(2)  # 実際のI/Oや計算をシミュレート
    print(f"[ASYNC LOG] Logged: '{message[:50]}...'", file=sys.stderr)


# --- 非同期イベントループを管理するクラス ---
class AsyncWorker:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.queue = queue.Queue()  # タスクをキューイングするためのスレッドセーフなキュー
        self.is_running = False

    def _run_loop(self):
        """asyncioイベントループを別スレッドで実行する"""
        asyncio.set_event_loop(self.loop)
        self.is_running = True
        try:
            # キューからコルーチンを取得して実行し続ける
            while True:
                coro = self.queue.get()
                if coro is None:  # 終了シグナル
                    break
                # コルーチンをタスクとしてスケジュール
                asyncio.ensure_future(coro, loop=self.loop)
                # キューのタスクが処理されるようにイベントループを短時間実行
                # Note: run_forever() と queue.get() の組み合わせは、
                # コルーチンが即座に実行されない場合にイベントループがアイドル状態になる可能性がある。
                # より堅牢な実装には loop.call_soon() でキューのポーリングをスケジュールする方法もある。
                # ここではシンプルさを優先。
                self.loop.run_until_complete(
                    asyncio.sleep(0)
                )  # イベントループを一度だけ実行し、スケジュールされたタスクを処理
        finally:
            # イベントループが終了する前に残りのタスクをキャンセルしてクリーンアップ
            pending = asyncio.all_tasks(self.loop)
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()
            self.is_running = False
            print("[ASYNC WORKER] Event loop closed.", file=sys.stderr)

    def start(self):
        """ワーカーを起動する"""
        if not self.thread.is_alive():
            self.thread.start()
            # イベントループが完全に起動するのを少し待つ
            # 実際のアプリケーションでは、より堅牢な同期メカニズムを使用すべき
            while not self.is_running:
                import time

                time.sleep(0.01)

    def stop(self):
        """ワーカーを停止する"""
        if self.thread.is_alive():
            # キューに終了シグナルを送信
            self.queue.put_nowait(None)
            self.thread.join(timeout=5)  # スレッドが終了するのを待つ
            if self.thread.is_alive():
                print(
                    "[ASYNC WORKER] Warning: Thread did not terminate gracefully.", file=sys.stderr
                )

    def run_async_task(self, coro):
        """メインスレッドから非同期タスクを投入する"""
        if self.is_running:
            # コルーチンをキューに入れて、イベントループスレッドで実行されるのを待つ
            self.queue.put_nowait(coro)
        else:
            print(
                "[ASYNC WORKER] Warning: Async worker not running. Task not submitted.",
                file=sys.stderr,
            )


# --- メインのPTYシェルロジック ---
def run_shell_with_async_backend():
    """
    PTYを介して対話型シェルを起動し、非同期バックエンドと連携する。
    """
    print(
        "PTYを介してシェルを起動します (終了するには 'exit' または Ctrl+D を押してください)。",
        file=sys.stderr,
    )

    # 非同期ワーカーを起動
    async_worker = AsyncWorker()
    async_worker.start()

    master_fd, slave_fd = pty.openpty()

    old_terminal_attrs = set_raw_mode(sys.stdin.fileno())
    if old_terminal_attrs is None:
        async_worker.stop()
        sys.exit(1)

    child_pid = os.fork()

    if child_pid == 0:  # 子プロセス
        os.close(master_fd)
        os.dup2(slave_fd, sys.stdin.fileno())
        os.dup2(slave_fd, sys.stdout.fileno())
        os.dup2(slave_fd, sys.stderr.fileno())
        os.close(slave_fd)
        os.setsid()
        try:
            fcntl.ioctl(sys.stdin.fileno(), termios.TIOCSCTTY, 0)
        except Exception as e:
            sys.stderr.write(f"Warning (child): Failed to set controlling terminal: {e}\n")
            sys.stderr.flush()

        shell = os.environ.get("SHELL", "/bin/bash")
        try:
            os.execv(shell, [shell, "-i"])
        except FileNotFoundError:
            sys.stderr.write(f"Error (child): Shell '{shell}' not found.\n")
            os._exit(1)
        except Exception as e:
            sys.stderr.write(f"Error (child): Failed to execute shell '{shell}': {e}\n")
            os._exit(1)

    else:  # 親プロセス
        os.close(slave_fd)

        # SIGWINCH (ターミナルサイズ変更) ハンドラ
        def handle_winch(signum, frame):
            try:
                buf = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
                ws = struct.unpack("HHHH", buf)
                rows, cols = ws[0], ws[1]
                pty.set_terminal_size(master_fd, rows, cols)
            except Exception as e:
                sys.stderr.write(f"Warning: SIGWINCH handling error: {e}\n")
                sys.stderr.flush()

        signal.signal(signal.SIGWINCH, handle_winch)

        # 出力バッファリング用
        output_buffer = []
        # キーワードを監視
        keywords_to_monitor = ["error", "warning", "fail"]

        try:
            while True:
                # select.select にタイムアウトを設定し、子プロセスの終了チェックも定期的に行えるようにする
                # タイムアウトがないと、I/Oがない場合に子プロセスの終了を検知できない
                rlist, _, _ = select.select([sys.stdin.fileno(), master_fd], [], [], 0.1)

                # ユーザーからの入力
                if sys.stdin.fileno() in rlist:
                    input_data = os.read(sys.stdin.fileno(), 4096)
                    if not input_data:  # EOF (Ctrl+D)
                        break
                    os.write(master_fd, input_data)

                # PTYマスターから出力 (シェルからの出力)
                if master_fd in rlist:
                    try:
                        output_data = os.read(master_fd, 4096)
                        if not output_data:  # EOF (子プロセスが終了)
                            break

                        sys.stdout.buffer.write(output_data)
                        sys.stdout.flush()

                        # 出力データをバッファに追加し、監視
                        output_text = output_data.decode("utf-8", errors="ignore")
                        output_buffer.append(output_text)

                        # バッファされた行を結合して監視
                        full_output_line = "".join(output_buffer)
                        if "\n" in full_output_line:
                            lines = full_output_line.splitlines(keepends=True)
                            for i, line in enumerate(lines):
                                if not line.endswith("\n") and i == len(lines) - 1:
                                    # 最後の行が不完全なら残しておく
                                    output_buffer = [line]
                                    break
                                else:
                                    # 完全な行を処理
                                    for keyword in keywords_to_monitor:
                                        if keyword in line.lower():
                                            print(
                                                f"\n[DETECTED] Keyword '{keyword}' in shell output: {line.strip()}",
                                                file=sys.stderr,
                                            )
                                            # ここで非同期タスクを投入
                                            async_worker.run_async_task(
                                                async_log(
                                                    f"Detected '{keyword}' in shell output: {line.strip()}"
                                                )
                                            )
                                            break
                            else:
                                # 全ての行が処理された
                                output_buffer = []  # バッファをクリア

                    except OSError as e:
                        if e.errno == errno.EIO:  # Input/output error (FD closed)
                            break
                        raise

                # 子プロセスが終了したかチェック (selectのタイムアウト時にも実行される)
                try:
                    # WNOHANG: 非ブロッキングモードで待機
                    pid, status = os.waitpid(child_pid, os.WNOHANG)
                    if pid == child_pid:  # 子プロセスが終了していた場合
                        print(
                            f"\n子プロセス (PID: {child_pid}) が終了しました。ステータス: {status}",
                            file=sys.stderr,
                        )
                        break
                except ChildProcessError:  # 子プロセスが既に終了している場合
                    break

        except InterruptedError:
            sys.stderr.write("\nセッションがシグナルによって中断されました。\n")
        except Exception as e:
            sys.stderr.write(f"メインループでエラーが発生しました: {e}\n")
        finally:
            # クリーンアップ
            restore_terminal_mode(sys.stdin.fileno(), old_terminal_attrs)
            if master_fd != -1:
                try:
                    os.close(master_fd)
                except OSError as e:
                    if e.errno != errno.EBADF:  # Bad file descriptor 以外ならログ
                        sys.stderr.write(f"Warning: Error closing master_fd {master_fd}: {e}\n")

            # 子プロセスがまだ生きていれば待機し、確実に終了させる
            if child_pid != -1:
                try:
                    os.waitpid(child_pid, 0)
                except ChildProcessError:
                    pass

            # 非同期ワーカーを停止
            async_worker.stop()

    print("アプリケーションが終了しました。", file=sys.stderr)


if __name__ == "__main__":
    run_shell_with_async_backend()
