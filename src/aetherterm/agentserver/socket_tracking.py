"""
Socket.IO Connection Tracking for Python Backend
Vue ↔ Python Socket.IO 連動確認用のPython側実装
"""

import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class RequestInfo:
    """受信したリクエスト情報"""

    request_id: str
    event_name: str
    timestamp: float
    data: Dict[str, Any]
    client_id: Optional[str] = None


@dataclass
class ResponseInfo:
    """送信したレスポンス情報"""

    request_id: str
    response_event: str
    duration: float
    success: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class EventMetrics:
    """イベント別メトリクス"""

    event_name: str
    request_count: int = 0
    response_count: int = 0
    average_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    error_count: int = 0
    success_rate: float = 0.0


class SocketConnectionTracker:
    """Socket.IO接続トラッキングクラス"""

    def __init__(self, enable_detailed_logging: bool = True, enable_metrics: bool = True):
        self.enable_detailed_logging = enable_detailed_logging
        self.enable_metrics = enable_metrics

        # Storage
        self.pending_requests: Dict[str, RequestInfo] = {}
        self.responses: List[ResponseInfo] = []
        self.event_metrics: Dict[str, EventMetrics] = {}

        # Callbacks
        self.error_callbacks: List[Callable[[RequestInfo, str], None]] = []
        self.slow_response_callbacks: List[Callable[[RequestInfo, float], None]] = []

        # Configuration
        self.slow_response_threshold = 1000  # ms

        if self.enable_detailed_logging:
            logger.info("🔗 Python Socket Connection Tracker initialized")

    def track_request(
        self, event_name: str, data: Dict[str, Any], client_id: Optional[str] = None
    ) -> str:
        """リクエストを追跡開始"""
        # Extract requestId from data if available
        request_id = data.get("_requestId")
        if not request_id:
            request_id = f"py_req_{int(time.time() * 1000)}_{len(self.pending_requests)}"

        timestamp = time.time()

        request_info = RequestInfo(
            request_id=request_id,
            event_name=event_name,
            timestamp=timestamp,
            data=self._sanitize_data(data),
            client_id=client_id,
        )

        self.pending_requests[request_id] = request_info

        # Update metrics
        if self.enable_metrics:
            if event_name not in self.event_metrics:
                self.event_metrics[event_name] = EventMetrics(event_name)
            self.event_metrics[event_name].request_count += 1

        if self.enable_detailed_logging:
            logger.info(f"📤 Socket request tracked: {event_name} [{request_id}]")

        return request_id

    def track_response(
        self,
        request_id: str,
        response_event: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """レスポンスを追跡"""
        if request_id not in self.pending_requests:
            if self.enable_detailed_logging:
                logger.warning(f"📥 Response for unknown request: {response_event} [{request_id}]")
            return

        request = self.pending_requests[request_id]
        timestamp = time.time()
        duration = (timestamp - request.timestamp) * 1000  # Convert to ms

        response_info = ResponseInfo(
            request_id=request_id,
            response_event=response_event,
            duration=duration,
            success=success,
            error=error,
            timestamp=timestamp,
        )

        self.responses.append(response_info)
        del self.pending_requests[request_id]

        # Update metrics
        if self.enable_metrics:
            event_name = request.event_name
            if event_name in self.event_metrics:
                metrics = self.event_metrics[event_name]
                metrics.response_count += 1

                # Update timing metrics
                if duration < metrics.min_time:
                    metrics.min_time = duration
                if duration > metrics.max_time:
                    metrics.max_time = duration

                # Recalculate average
                total_time = metrics.average_time * (metrics.response_count - 1) + duration
                metrics.average_time = total_time / metrics.response_count

                # Update error count
                if not success:
                    metrics.error_count += 1

                # Update success rate
                metrics.success_rate = (
                    metrics.response_count - metrics.error_count
                ) / metrics.response_count

        # Check for slow response
        if duration > self.slow_response_threshold:
            for callback in self.slow_response_callbacks:
                try:
                    callback(request, duration)
                except Exception as e:
                    logger.error(f"Error in slow response callback: {e}")

        # Check for error
        if not success and error:
            for callback in self.error_callbacks:
                try:
                    callback(request, error)
                except Exception as e:
                    logger.error(f"Error in error callback: {e}")

        if self.enable_detailed_logging:
            status = "✅" if success else "❌"
            logger.info(
                f"📥 Socket response tracked: {response_event} {status} [{request_id}] ({duration:.1f}ms)"
            )

    def track_error(self, request_id: str, error: str) -> None:
        """エラーを追跡"""
        self.track_response(request_id, "error", success=False, error=error)

    def get_pending_requests(self) -> List[RequestInfo]:
        """保留中のリクエスト一覧を取得"""
        return list(self.pending_requests.values())

    def get_metrics(self) -> Dict[str, Any]:
        """メトリクスを取得"""
        if not self.enable_metrics:
            return {}

        total_requests = sum(m.request_count for m in self.event_metrics.values())
        total_responses = len(self.responses)
        error_count = sum(m.error_count for m in self.event_metrics.values())

        response_times = [r.duration for r in self.responses]
        average_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_requests": total_requests,
            "total_responses": total_responses,
            "average_response_time": average_response_time,
            "error_count": error_count,
            "pending_count": len(self.pending_requests),
            "event_metrics": {
                name: {
                    "event_name": metrics.event_name,
                    "request_count": metrics.request_count,
                    "response_count": metrics.response_count,
                    "average_time": metrics.average_time,
                    "min_time": metrics.min_time if metrics.min_time != float("inf") else 0,
                    "max_time": metrics.max_time,
                    "error_count": metrics.error_count,
                    "success_rate": metrics.success_rate,
                }
                for name, metrics in self.event_metrics.items()
            },
        }

    def clear_metrics(self) -> None:
        """メトリクスをクリア"""
        self.responses.clear()
        self.event_metrics.clear()

        if self.enable_detailed_logging:
            logger.info("📊 Socket metrics cleared")

    def on_error(self, callback: Callable[[RequestInfo, str], None]) -> None:
        """エラーコールバックを登録"""
        self.error_callbacks.append(callback)

    def on_slow_response(self, callback: Callable[[RequestInfo, float], None]) -> None:
        """低速レスポンスコールバックを登録"""
        self.slow_response_callbacks.append(callback)

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """データをサニタイズ（ログ用）"""
        try:
            sanitized = dict(data)

            # Remove sensitive data
            sensitive_keys = ["password", "token", "auth", "secret"]
            for key in sensitive_keys:
                if key in sanitized:
                    sanitized[key] = "***"

            # Truncate large strings
            for key, value in sanitized.items():
                if isinstance(value, str) and len(value) > 100:
                    sanitized[key] = value[:100] + "..."

            return sanitized
        except Exception:
            return {"_sanitized": True}


class NoOpSocketConnectionTracker:
    """何もしないトラッカー（Null Object Pattern）"""

    def track_request(
        self, event_name: str, data: Dict[str, Any], client_id: Optional[str] = None
    ) -> str:
        return "noop"

    def track_response(
        self,
        request_id: str,
        response_event: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        pass

    def track_error(self, request_id: str, error: str) -> None:
        pass

    def get_pending_requests(self) -> List[RequestInfo]:
        return []

    def get_metrics(self) -> Dict[str, Any]:
        return {}

    def clear_metrics(self) -> None:
        pass

    def on_error(self, callback: Callable[[RequestInfo, str], None]) -> None:
        pass

    def on_slow_response(self, callback: Callable[[RequestInfo, float], None]) -> None:
        pass


# Global tracker instance
_tracker_instance: Optional[SocketConnectionTracker] = None


def get_socket_tracker() -> SocketConnectionTracker:
    """グローバルトラッカーインスタンスを取得"""
    global _tracker_instance
    if _tracker_instance is None:
        # Check if tracking is enabled
        import os

        tracking_enabled = os.getenv("SOCKET_TRACKING_ENABLED", "false").lower() == "true"

        if tracking_enabled:
            _tracker_instance = SocketConnectionTracker()
        else:
            _tracker_instance = NoOpSocketConnectionTracker()

    return _tracker_instance


def track_socket_request(
    event_name: str, data: Dict[str, Any], client_id: Optional[str] = None
) -> str:
    """Socket.IOリクエストを追跡"""
    return get_socket_tracker().track_request(event_name, data, client_id)


def track_socket_response(
    request_id: str, response_event: str, success: bool = True, error: Optional[str] = None
) -> None:
    """Socket.IOレスポンスを追跡"""
    get_socket_tracker().track_response(request_id, response_event, success, error)


def track_socket_error(request_id: str, error: str) -> None:
    """Socket.IOエラーを追跡"""
    get_socket_tracker().track_error(request_id, error)
