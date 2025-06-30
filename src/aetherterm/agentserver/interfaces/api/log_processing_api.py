"""
Log Processing API for AetherTerm AgentServer

Provides REST and WebSocket endpoints for log monitoring and processing.
"""

import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from aetherterm.agentserver.terminals.asyncio_terminal import AsyncioTerminal

log = logging.getLogger("aetherterm.log_processing_api")

# Initialize router
router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/recent")
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000, description="Number of recent logs to retrieve"),
    category: Optional[str] = Query(None, description="Filter by log category"),
) -> JSONResponse:
    """Get recent processed logs with optional filtering."""
    try:
        logs = AsyncioTerminal.get_recent_logs(limit=limit, category=category)
        return JSONResponse(
            {"logs": logs, "count": len(logs), "limit": limit, "category": category}
        )
    except Exception as e:
        log.error(f"Error retrieving recent logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/statistics")
async def get_log_statistics() -> JSONResponse:
    """Get statistics about processed logs."""
    try:
        stats = AsyncioTerminal.get_log_statistics()
        return JSONResponse(stats)
    except Exception as e:
        log.error(f"Error retrieving log statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/categories")
async def get_log_categories() -> JSONResponse:
    """Get available log categories and their patterns."""
    try:
        categories = {
            category: {
                "patterns": patterns,
                "severity": AsyncioTerminal._get_severity(category),
                "description": _get_category_description(category),
            }
            for category, patterns in AsyncioTerminal.log_patterns.items()
        }

        # Add dynamic categories
        categories.update(
            {
                "command": {
                    "patterns": ["^\\$|#"],
                    "severity": 1,
                    "description": "Shell commands and prompts",
                },
                "system": {
                    "patterns": ["system", "kernel", "daemon"],
                    "severity": 3,
                    "description": "System-level messages",
                },
                "general": {
                    "patterns": ["*"],
                    "severity": 1,
                    "description": "General output and uncategorized messages",
                },
            }
        )

        return JSONResponse(categories)
    except Exception as e:
        log.error(f"Error retrieving log categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


@router.websocket("/stream")
async def log_stream_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()
    log.info(f"New log stream WebSocket connection from {websocket.client}")

    # Subscribe to log updates
    AsyncioTerminal.subscribe_to_logs(websocket)

    try:
        # Send initial log batch
        recent_logs = AsyncioTerminal.get_recent_logs(limit=50)
        if recent_logs:
            initial_message = {
                "type": "initial_logs",
                "logs": recent_logs,
                "count": len(recent_logs),
            }
            await websocket.send_text(json.dumps(initial_message))

        # Send current statistics
        stats = AsyncioTerminal.get_log_statistics()
        stats_message = {"type": "statistics", "data": stats}
        await websocket.send_text(json.dumps(stats_message))

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (e.g., filter requests)
                data = await websocket.receive_text()
                message = json.loads(data)

                await _handle_websocket_message(websocket, message)

            except WebSocketDisconnect:
                log.info("Log stream WebSocket disconnected")
                break
            except json.JSONDecodeError:
                log.warning("Invalid JSON received from log stream WebSocket")
                error_message = {"type": "error", "message": "Invalid JSON format"}
                await websocket.send_text(json.dumps(error_message))
            except Exception as e:
                log.error(f"Error in log stream WebSocket: {e}")
                error_message = {"type": "error", "message": str(e)}
                await websocket.send_text(json.dumps(error_message))

    except WebSocketDisconnect:
        log.info("Log stream WebSocket disconnected")
    except Exception as e:
        log.error(f"Unexpected error in log stream WebSocket: {e}")
    finally:
        # Unsubscribe from log updates
        AsyncioTerminal.unsubscribe_from_logs(websocket)
        log.info("Log stream WebSocket connection closed")


async def _handle_websocket_message(websocket: WebSocket, message: Dict):
    """Handle incoming WebSocket messages from clients."""
    try:
        message_type = message.get("type")

        if message_type == "get_logs":
            # Client requesting specific logs
            limit = message.get("limit", 100)
            category = message.get("category")

            logs = AsyncioTerminal.get_recent_logs(limit=limit, category=category)
            response = {
                "type": "logs_response",
                "logs": logs,
                "count": len(logs),
                "request_id": message.get("request_id"),
            }
            await websocket.send_text(json.dumps(response))

        elif message_type == "get_statistics":
            # Client requesting current statistics
            stats = AsyncioTerminal.get_log_statistics()
            response = {
                "type": "statistics_response",
                "data": stats,
                "request_id": message.get("request_id"),
            }
            await websocket.send_text(json.dumps(response))

        elif message_type == "ping":
            # Client ping for connection health check
            response = {"type": "pong", "timestamp": message.get("timestamp")}
            await websocket.send_text(json.dumps(response))

        else:
            # Unknown message type
            response = {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "request_id": message.get("request_id"),
            }
            await websocket.send_text(json.dumps(response))

    except Exception as e:
        log.error(f"Error handling WebSocket message: {e}")
        error_response = {
            "type": "error",
            "message": "Failed to process message",
            "request_id": message.get("request_id"),
        }
        await websocket.send_text(json.dumps(error_response))


def _get_category_description(category: str) -> str:
    """Get human-readable description for log categories."""
    descriptions = {
        "error": "Error messages and exceptions",
        "warning": "Warning messages and deprecation notices",
        "info": "Informational messages and status updates",
        "success": "Success messages and completion notices",
        "command": "Shell commands and prompts",
        "system": "System-level messages and kernel output",
        "general": "General output and uncategorized messages",
    }
    return descriptions.get(category, "Unknown category")


@router.post("/start-processing")
async def start_log_processing() -> JSONResponse:
    """Start the log processing task."""
    try:
        await AsyncioTerminal.start_log_processing()
        return JSONResponse({"status": "success", "message": "Log processing started"})
    except Exception as e:
        log.error(f"Error starting log processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to start log processing")


@router.post("/stop-processing")
async def stop_log_processing() -> JSONResponse:
    """Stop the log processing task."""
    try:
        await AsyncioTerminal.stop_log_processing()
        return JSONResponse({"status": "success", "message": "Log processing stopped"})
    except Exception as e:
        log.error(f"Error stopping log processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop log processing")


@router.get("/processing-status")
async def get_processing_status() -> JSONResponse:
    """Get the current status of log processing."""
    try:
        is_running = (
            AsyncioTerminal.log_processing_task is not None
            and not AsyncioTerminal.log_processing_task.done()
        )

        status = {
            "running": is_running,
            "buffer_size": len(AsyncioTerminal.log_buffer),
            "processed_count": len(AsyncioTerminal.processed_logs),
            "subscribers": len(AsyncioTerminal.log_subscribers),
        }

        return JSONResponse(status)
    except Exception as e:
        log.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get processing status")


import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...langchain.config.storage_config import StorageConfig
from ...logprocessing.log_processing_manager import LogProcessingManager

logger = logging.getLogger(__name__)

# FastAPI Router
router = APIRouter(prefix="/api/log-processing", tags=["log-processing"])

# Global log processing manager
log_processing_manager: Optional[LogProcessingManager] = None


# Pydantic Models
class TerminalRequest(BaseModel):
    terminal_id: str
    log_file_path: str


class SimulateOutputRequest(BaseModel):
    terminal_id: str
    output: str
    level: str = "INFO"
    timestamp: Optional[str] = None


class StressTestRequest(BaseModel):
    test_size: int = 1000


# API Endpoints


@router.post("/initialize")
async def initialize_log_processing():
    """ログ処理システムを初期化"""
    global log_processing_manager

    try:
        if log_processing_manager is not None:
            logger.warning("Log processing manager already initialized")
            return {
                "status": "already_initialized",
                "message": "Log processing system is already running",
            }

        # Storage configuration
        storage_config = StorageConfig()

        # Initialize log processing manager
        log_processing_manager = LogProcessingManager(storage_config)
        await log_processing_manager.initialize()

        # Start background processing
        asyncio.create_task(log_processing_manager.start_processing())

        logger.info("Log processing system initialized successfully")
        return {"status": "success", "message": "Log processing system initialized"}

    except Exception as e:
        logger.error(f"Failed to initialize log processing system: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {e!s}")


@router.post("/terminals")
async def add_terminal(request: TerminalRequest):
    """新しいターミナルを監視対象に追加"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        await log_processing_manager.add_terminal(request.terminal_id, request.log_file_path)

        logger.info(f"Added terminal: {request.terminal_id}")
        return {
            "status": "success",
            "message": f"Terminal {request.terminal_id} added successfully",
        }

    except Exception as e:
        logger.error(f"Failed to add terminal {request.terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add terminal: {e!s}")


@router.delete("/terminals/{terminal_id}")
async def remove_terminal(terminal_id: str):
    """ターミナルを監視対象から削除"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        await log_processing_manager.remove_terminal(terminal_id)

        logger.info(f"Removed terminal: {terminal_id}")
        return {"status": "success", "message": f"Terminal {terminal_id} removed successfully"}

    except Exception as e:
        logger.error(f"Failed to remove terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove terminal: {e!s}")


@router.get("/statistics")
async def get_system_statistics():
    """システム統計情報を取得"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        stats = await log_processing_manager.get_system_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get system statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {e!s}")


@router.get("/terminal/{terminal_id}/statistics")
async def get_terminal_statistics(terminal_id: str):
    """指定ターミナルの統計情報を取得"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        stats = await log_processing_manager.get_terminal_summary(terminal_id)
        return stats

    except Exception as e:
        logger.error(f"Failed to get terminal statistics for {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get terminal statistics: {e!s}")


@router.get("/terminal/{terminal_id}/logs")
async def get_terminal_logs(terminal_id: str, limit: int = Query(default=50, le=500)):
    """指定ターミナルの最近のログを取得"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        logs = await log_processing_manager.get_recent_logs(terminal_id, limit)
        return logs

    except Exception as e:
        logger.error(f"Failed to get logs for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e!s}")


@router.get("/terminal/{terminal_id}/errors")
async def get_terminal_errors(terminal_id: str):
    """指定ターミナルのエラーログを取得"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        errors = await log_processing_manager.search_structured_logs(
            query="", terminal_id=terminal_id, error_level="ERROR", limit=50
        )
        return errors

    except Exception as e:
        logger.error(f"Failed to get errors for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get errors: {e!s}")


@router.get("/terminal/{terminal_id}/patterns")
async def get_terminal_patterns(terminal_id: str):
    """指定ターミナルのパターンを取得"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        patterns = await log_processing_manager.search_patterns(
            query_text=f"terminal:{terminal_id}", limit=20
        )
        return patterns

    except Exception as e:
        logger.error(f"Failed to get patterns for terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {e!s}")


@router.get("/search")
async def search_logs(
    q: str = Query(..., description="Search query"),
    terminal_id: Optional[str] = Query(None, description="Filter by terminal ID"),
    log_level: Optional[str] = Query(None, description="Filter by log level"),
    data_source: Optional[str] = Query(
        None, description="Data source: recent, structured, patterns"
    ),
    limit: int = Query(default=50, le=200, description="Maximum number of results"),
):
    """ログ検索"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        # 統合検索を実行
        results = await log_processing_manager.process_immediate_query(q, terminal_id)

        # データソースフィルタリング
        if data_source:
            if data_source == "recent":
                filtered_results = results.get("results", {}).get("recent_logs", [])
            elif data_source == "structured":
                filtered_results = results.get("results", {}).get("structured_logs", [])
            elif data_source == "patterns":
                filtered_results = results.get("results", {}).get("patterns", [])
            else:
                filtered_results = []
        else:
            # 全データソースを統合
            all_results = []
            for source, data in results.get("results", {}).items():
                if isinstance(data, list):
                    for item in data:
                        item["source"] = source.replace("_logs", "").replace("_", "")
                        all_results.append(item)
            filtered_results = all_results

        # ログレベルフィルタリング
        if log_level and filtered_results:
            filtered_results = [
                result for result in filtered_results if result.get("error_level") == log_level
            ]

        # 制限適用
        filtered_results = filtered_results[:limit]

        return {
            "query": q,
            "filters": {
                "terminal_id": terminal_id,
                "log_level": log_level,
                "data_source": data_source,
            },
            "results": filtered_results,
            "total_results": len(filtered_results),
            "search_time": 100,  # Mock value
        }

    except Exception as e:
        logger.error(f"Search failed for query '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}")


@router.post("/simulate-output")
async def simulate_output(request: SimulateOutputRequest):
    """テスト用のターミナル出力をシミュレート"""
    global log_processing_manager

    if log_processing_manager is None:
        raise HTTPException(status_code=400, detail="Log processing system not initialized")

    try:
        # Redisに直接ログエントリを作成
        redis_storage = log_processing_manager.redis_storage

        timestamp = request.timestamp or datetime.utcnow().isoformat()
        log_entry = {
            "terminal_id": request.terminal_id,
            "timestamp": timestamp,
            "raw_output": request.output,
            "size": len(request.output),
            "line_count": request.output.count("\n") + 1,
            "simulated": True,
            "level": request.level,
        }

        # Redisキー生成
        import time

        log_key = f"terminal_logs:{request.terminal_id}:{int(time.time() * 1000)}"

        # Redis保存
        await redis_storage.set_with_ttl(key=log_key, value=json.dumps(log_entry), ttl_seconds=3600)

        # ターミナル別ログリストに追加
        list_key = f"terminal_logs:list:{request.terminal_id}"
        await redis_storage.list_push(list_key, log_key)
        await redis_storage.expire(list_key, 3600)

        return {
            "status": "success",
            "message": f"Simulated output for terminal {request.terminal_id}",
        }

    except Exception as e:
        logger.error(f"Failed to simulate output for {request.terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to simulate output: {e!s}")


@router.post("/test-error-patterns")
async def test_error_patterns():
    """エラーパターンテスト"""
    try:
        # モックエラーパターンを生成
        error_patterns = [
            "FileNotFoundError: [Errno 2] No such file or directory",
            "PermissionError: [Errno 13] Permission denied",
            "ConnectionError: Failed to establish connection",
            "TypeError: 'NoneType' object is not subscriptable",
            "ValueError: invalid literal for int() with base 10",
        ]

        for i, pattern in enumerate(error_patterns):
            await simulate_output(
                SimulateOutputRequest(
                    terminal_id=f"test-terminal-{i % 3}", output=pattern, level="ERROR"
                )
            )

        return {
            "status": "success",
            "patterns_detected": len(error_patterns),
            "message": "Error pattern test completed",
        }

    except Exception as e:
        logger.error(f"Error pattern test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error pattern test failed: {e!s}")


@router.post("/test-command-patterns")
async def test_command_patterns():
    """コマンドパターンテスト"""
    try:
        command_patterns = [
            "$ npm install express",
            "$ git commit -m 'Update feature'",
            "$ sudo systemctl restart nginx",
            "$ docker run -d nginx",
            "$ python manage.py migrate",
        ]

        for i, pattern in enumerate(command_patterns):
            await simulate_output(
                SimulateOutputRequest(
                    terminal_id=f"test-terminal-{i % 2}", output=pattern, level="INFO"
                )
            )

        return {
            "status": "success",
            "patterns_detected": len(command_patterns),
            "message": "Command pattern test completed",
        }

    except Exception as e:
        logger.error(f"Command pattern test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Command pattern test failed: {e!s}")


@router.post("/stress-test-storage")
async def stress_test_storage(request: StressTestRequest):
    """ストレージストレステスト"""
    try:
        import os
        import time

        import psutil

        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # 大量のログエントリを生成
        tasks = []
        for i in range(request.test_size):
            tasks.append(
                simulate_output(
                    SimulateOutputRequest(
                        terminal_id=f"stress-test-{i % 10}",
                        output=f"Stress test log entry {i} with additional content to test storage performance",
                        level="INFO" if i % 5 != 0 else "WARNING",
                    )
                )
            )

        await asyncio.gather(*tasks)

        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        duration = (end_time - start_time) * 1000  # ms
        memory_usage = end_memory - start_memory

        return {
            "status": "success",
            "test_size": request.test_size,
            "duration": round(duration, 2),
            "memory_usage": round(memory_usage, 2),
            "throughput": round(request.test_size / (duration / 1000), 2),
            "message": f"Storage stress test completed: {request.test_size} entries in {duration:.2f}ms",
        }

    except Exception as e:
        logger.error(f"Storage stress test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Storage stress test failed: {e!s}")


@router.delete("/clear-test-data")
async def clear_test_data():
    """テストデータをクリア"""
    global log_processing_manager

    try:
        if log_processing_manager is not None:
            await log_processing_manager.shutdown()
            log_processing_manager = None

        return {
            "status": "success",
            "message": "Test data cleared and log processing system stopped",
        }

    except Exception as e:
        logger.error(f"Failed to clear test data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear test data: {e!s}")


@router.get("/health")
async def health_check():
    """ヘルスチェック"""
    global log_processing_manager

    return {
        "status": "ok",
        "log_processing_initialized": log_processing_manager is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }
