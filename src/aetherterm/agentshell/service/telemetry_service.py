"""
テレメトリーサービス (Stub Implementation)

OpenTelemetryの依存関係なしで動作するスタブ実装
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    テレメトリーサービス (Stub Implementation)

    分散トレーシング、メトリクス収集、ログ相関機能を提供
    """

    def __init__(self, config=None):
        self.config = config
        self._initialized = False

    def initialize(self) -> None:
        """OpenTelemetryを初期化"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("TelemetryService initialized (stub mode)")

    def start_span(self, name: str, **kwargs):
        """Start a tracing span (stub)"""
        return StubSpan()

    def record_session_start(self, session_id: str):
        """Record session start (stub)"""
        pass

    def record_session_end(self, session_id: str, duration: float):
        """Record session end (stub)"""
        pass

    def record_terminal_event(self, event_type: str, session_id: str):
        """Record terminal event (stub)"""
        pass

    def record_ai_request(self, request_type: str, duration: float):
        """Record AI request (stub)"""
        pass

    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """Trace operation (stub)"""
        yield

    def shutdown(self):
        """Shutdown telemetry (stub)"""
        pass

    def is_initialized(self) -> bool:
        """初期化済みかどうかを確認"""
        return self._initialized


class StubSpan:
    """Stub span for testing"""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key: str, value: Any):
        pass
