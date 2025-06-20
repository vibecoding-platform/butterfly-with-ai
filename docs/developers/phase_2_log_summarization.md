# Phase 2: ログ要約機能 - 詳細設計仕様

## 1. 概要

LangChain統合の第2フェーズとして、ターミナルログの要約機能を実装します。
リアルタイム要約、セッション要約、日次要約の3層構造で効率的なログ管理を実現します。

## 2. 要約アーキテクチャ

### 2.1 要約レベル構造
```
┌─────────────────────────────────────────────────────────────┐
│                    ログ要約システム                          │
├─────────────────────────────────────────────────────────────┤
│  リアルタイム要約 (5分間隔)                                 │
│  ├── コマンド実行ログ                                       │
│  ├── エラー・警告ログ                                       │
│  └── システムイベント                                       │
├─────────────────────────────────────────────────────────────┤
│  セッション要約 (セッション終了時)                          │
│  ├── リアルタイム要約の統合                                 │
│  ├── 主要アクティビティの抽出                               │
│  └── 問題・解決パターンの識別                               │
├─────────────────────────────────────────────────────────────┤
│  日次要約 (日次バッチ処理)                                  │
│  ├── セッション要約の統合                                   │
│  ├── 傾向分析                                               │
│  └── 推奨事項の生成                                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 LangChain統合パターン
```python
# 要約チェーンの構成例
summarization_chain = (
    PromptTemplate.from_template(SUMMARIZATION_PROMPT) 
    | llm 
    | StrOutputParser()
    | SummaryPostProcessor()
)
```

## 3. コンポーネント詳細設計

### 3.1 ログ処理パイプライン (`summarization/log_processor.py`)

```python
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate

from ..memory.models import LogSummary
from ..config import LangChainConfig

logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """ログレベル"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class LogEntry:
    """ログエントリ"""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str  # terminal, system, application
    session_id: str
    metadata: Dict[str, Any]
    
    def to_document(self) -> Document:
        """LangChain Documentに変換"""
        return Document(
            page_content=f"[{self.timestamp.isoformat()}] {self.level.value}: {self.message}",
            metadata={
                "timestamp": self.timestamp.isoformat(),
                "level": self.level.value,
                "source": self.source,
                "session_id": self.session_id,
                **self.metadata
            }
        )

class LogProcessor:
    """ログ処理クラス"""
    
    def __init__(self, config: LangChainConfig):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n", " ", ""]
        )
        self._log_buffer: List[LogEntry] = []
        self._last_process_time = datetime.utcnow()
    
    async def add_log_entry(self, entry: LogEntry) -> None:
        """ログエントリを追加"""
        self._log_buffer.append(entry)
        
        # バッファサイズまたは時間間隔でトリガー
        if (len(self._log_buffer) >= self.config.max_log_entries_per_summary or
            datetime.utcnow() - self._last_process_time >= 
            timedelta(minutes=self.config.realtime_interval_minutes)):
            await self._process_buffer()
    
    async def _process_buffer(self) -> List[Document]:
        """バッファ内のログを処理"""
        if not self._log_buffer:
            return []
        
        try:
            # ログエントリをDocumentに変換
            documents = [entry.to_document() for entry in self._log_buffer]
            
            # テキスト分割
            split_docs = self.text_splitter.split_documents(documents)
            
            # バッファをクリア
            processed_entries = self._log_buffer.copy()
            self._log_buffer.clear()
            self._last_process_time = datetime.utcnow()
            
            logger.info(f"ログバッファを処理しました: {len(processed_entries)}件")
            return split_docs
            
        except Exception as e:
            logger.error(f"ログ処理中にエラーが発生: {e}")
            raise
    
    def categorize_logs(self, logs: List[LogEntry]) -> Dict[str, List[LogEntry]]:
        """ログをカテゴリ別に分類"""
        categories = {
            "commands": [],
            "errors": [],
            "warnings": [],
            "system_events": [],
            "user_actions": []
        }
        
        for log in logs:
            if "command executed" in log.message.lower():
                categories["commands"].append(log)
            elif log.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                categories["errors"].append(log)
            elif log.level == LogLevel.WARN:
                categories["warnings"].append(log)
            elif log.source == "system":
                categories["system_events"].append(log)
            else:
                categories["user_actions"].append(log)
        
        return categories
    
    def extract_command_patterns(self, command_logs: List[LogEntry]) -> Dict[str, Any]:
        """コマンドパターンを抽出"""
        commands = []
        for log in command_logs:
            # "Command executed: " の後のコマンドを抽出
            if "command executed:" in log.message.lower():
                cmd = log.message.split(":", 1)[1].strip()
                commands.append(cmd)
        
        # コマンド頻度分析
        command_freq = {}
        for cmd in commands:
            base_cmd = cmd.split()[0] if cmd.split() else cmd
            command_freq[base_cmd] = command_freq.get(base_cmd, 0) + 1
        
        return {
            "total_commands": len(commands),
            "unique_commands": len(set(commands)),
            "command_frequency": command_freq,
            "most_used_commands": sorted(command_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        }
```

### 3.2 要約エンジン (`summarization/log_summarizer.py`)

```python
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.chains import LLMChain

from .log_processor import LogProcessor, LogEntry, LogLevel
from ..memory.models import LogSummary
from ..config import LangChainConfig

logger = logging.getLogger(__name__)

class LogSummarizationService:
    """ログ要約サービス"""
    
    def __init__(self, config: LangChainConfig, memory_manager):
        self.config = config
        self.memory_manager = memory_manager
        self.log_processor = LogProcessor(config)
        
        # LLMの初期化
        self.llm = ChatOpenAI(
            model_name=config.summarization_model,
            max_tokens=config.summary_max_tokens,
            temperature=0.3,
            openai_api_key=config.openai_api_key
        )
        
        # プロンプトテンプレートの設定
        self._setup_prompts()
        
        # 要約チェーンの構築
        self._setup_chains()
    
    def _setup_prompts(self) -> None:
        """プロンプトテンプレートを設定"""
        
        # リアルタイム要約用プロンプト
        self.realtime_prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたはターミナルログの分析専門家です。
以下のログエントリを分析し、簡潔で有用な要約を作成してください。

要約には以下を含めてください：
1. 主要なアクティビティ
2. 実行されたコマンドの概要
3. エラーや警告の要約
4. 注目すべき点や異常

要約は日本語で、200文字以内で作成してください。"""),
            ("user", "ログエントリ:\n{logs}\n\n要約を作成してください。")
        ])
        
        # セッション要約用プロンプト
        self.session_prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたはターミナルセッションの分析専門家です。
セッション全体のリアルタイム要約を統合し、包括的なセッション要約を作成してください。

要約には以下を含めてください：
1. セッションの目的と主要なタスク
2. 実行されたコマンドの流れ
3. 発生した問題と解決方法
4. 学習ポイントや改善提案
5. セッションの成果

要約は日本語で、500文字以内で作成してください。"""),
            ("user", "リアルタイム要約:\n{summaries}\n\nセッション統計:\n{statistics}\n\nセッション要約を作成してください。")
        ])
        
        # 日次要約用プロンプト
        self.daily_prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたは日次アクティビティの分析専門家です。
複数のセッション要約を統合し、1日の活動全体を俯瞰した要約を作成してください。

要約には以下を含めてください：
1. 1日の主要な作業内容
2. 生産性の傾向
3. 頻繁に発生した問題
4. 学習した技術やコマンド
5. 明日への改善提案

要約は日本語で、800文字以内で作成してください。"""),
            ("user", "セッション要約:\n{session_summaries}\n\n日次統計:\n{daily_statistics}\n\n日次要約を作成してください。")
        ])
    
    def _setup_chains(self) -> None:
        """要約チェーンを構築"""
        self.realtime_chain = LLMChain(
            llm=self.llm,
            prompt=self.realtime_prompt,
            verbose=self.config.debug
        )
        
        self.session_chain = LLMChain(
            llm=self.llm,
            prompt=self.session_prompt,
            verbose=self.config.debug
        )
        
        self.daily_chain = LLMChain(
            llm=self.llm,
            prompt=self.daily_prompt,
            verbose=self.config.debug
        )
    
    async def create_realtime_summary(
        self, 
        logs: List[LogEntry], 
        session_id: str
    ) -> LogSummary:
        """
        リアルタイム要約を作成
        
        Args:
            logs: ログエントリリスト
            session_id: セッションID
            
        Returns:
            LogSummary: 要約結果
        """
        try:
            if not logs:
                return self._create_empty_summary(session_id, "realtime")
            
            # ログを分類
            categorized_logs = self.log_processor.categorize_logs(logs)
            
            # コマンドパターンを抽出
            command_patterns = self.log_processor.extract_command_patterns(
                categorized_logs["commands"]
            )
            
            # ログテキストを準備
            log_text = self._format_logs_for_summary(logs)
            
            # AI要約を生成
            summary_response = await self.realtime_chain.arun(
                logs=log_text
            )
            
            # 要約オブジェクトを作成
            summary = LogSummary(
                session_id=session_id,
                summary_type="realtime",
                content=summary_response,
                log_count=len(logs),
                start_time=min(log.timestamp for log in logs),
                end_time=max(log.timestamp for log in logs),
                metadata={
                    "categorized_counts": {k: len(v) for k, v in categorized_logs.items()},
                    "command_patterns": command_patterns,
                    "error_count": len(categorized_logs["errors"]),
                    "warning_count": len(categorized_logs["warnings"])
                }
            )
            
            logger.info(f"リアルタイム要約を作成しました: {len(logs)}件のログ")
            return summary
            
        except Exception as e:
            logger.error(f"リアルタイム要約作成中にエラー: {e}")
            raise
    
    async def create_session_summary(self, session_id: str) -> LogSummary:
        """
        セッション要約を作成
        
        Args:
            session_id: セッションID
            
        Returns:
            LogSummary: セッション要約
        """
        try:
            # セッションのリアルタイム要約を取得
            realtime_summaries = await self.memory_manager.get_summaries(
                session_id=session_id,
                summary_type="realtime"
            )
            
            if not realtime_summaries:
                return self._create_empty_summary(session_id, "session")
            
            # セッション統計を取得
            session_stats = await self.memory_manager.get_session_statistics(session_id)
            
            # 要約テキストを準備
            summaries_text = "\n".join([s.content for s in realtime_summaries])
            statistics_text = self._format_statistics(session_stats)
            
            # AI要約を生成
            session_summary_response = await self.session_chain.arun(
                summaries=summaries_text,
                statistics=statistics_text
            )
            
            # セッション要約オブジェクトを作成
            summary = LogSummary(
                session_id=session_id,
                summary_type="session",
                content=session_summary_response,
                log_count=sum(s.log_count for s in realtime_summaries),
                start_time=min(s.start_time for s in realtime_summaries),
                end_time=max(s.end_time for s in realtime_summaries),
                metadata={
                    "realtime_summary_count": len(realtime_summaries),
                    "session_duration_minutes": session_stats.get("duration_minutes", 0),
                    "total_commands": session_stats.get("total_commands", 0),
                    "unique_commands": session_stats.get("unique_commands", 0),
                    "error_rate": session_stats.get("error_rate", 0.0)
                }
            )
            
            logger.info(f"セッション要約を作成しました: セッション{session_id}")
            return summary
            
        except Exception as e:
            logger.error(f"セッション要約作成中にエラー: {e}")
            raise
    
    async def create_daily_summary(self, date: datetime) -> LogSummary:
        """
        日次要約を作成
        
        Args:
            date: 対象日付
            
        Returns:
            LogSummary: 日次要約
        """
        try:
            # 指定日のセッション要約を取得
            session_summaries = await self.memory_manager.get_daily_session_summaries(date)
            
            if not session_summaries:
                return self._create_empty_summary("daily", "daily")
            
            # 日次統計を計算
            daily_stats = self._calculate_daily_statistics(session_summaries)
            
            # 要約テキストを準備
            session_summaries_text = "\n\n".join([
                f"セッション {s.session_id}:\n{s.content}" 
                for s in session_summaries
            ])
            daily_statistics_text = self._format_statistics(daily_stats)
            
            # AI要約を生成
            daily_summary_response = await self.daily_chain.arun(
                session_summaries=session_summaries_text,
                daily_statistics=daily_statistics_text
            )
            
            # 日次要約オブジェクトを作成
            summary = LogSummary(
                session_id=f"daily-{date.strftime('%Y-%m-%d')}",
                summary_type="daily",
                content=daily_summary_response,
                log_count=sum(s.log_count for s in session_summaries),
                start_time=date.replace(hour=0, minute=0, second=0, microsecond=0),
                end_time=date.replace(hour=23, minute=59, second=59, microsecond=999999),
                metadata={
                    "session_count": len(session_summaries),
                    "total_duration_minutes": daily_stats.get("total_duration_minutes", 0),
                    "total_commands": daily_stats.get("total_commands", 0),
                    "average_session_duration": daily_stats.get("average_session_duration", 0),
                    "most_active_hour": daily_stats.get("most_active_hour", 0),
                    "productivity_score": daily_stats.get("productivity_score", 0.0)
                }
            )
            
            logger.info(f"日次要約を作成しました: {date.strftime('%Y-%m-%d')}")
            return summary
            
        except Exception as e:
            logger.error(f"日次要約作成中にエラー: {e}")
            raise
    
    def _format_logs_for_summary(self, logs: List[LogEntry]) -> str:
        """要約用にログをフォーマット"""
        formatted_logs = []
        for log in logs:
            formatted_logs.append(
                f"[{log.timestamp.strftime('%H:%M:%S')}] {log.level.value}: {log.message}"
            )
        return "\n".join(formatted_logs)
    
    def _format_statistics(self, stats: Dict[str, Any]) -> str:
        """統計情報をフォーマット"""
        formatted_stats = []
        for key, value in stats.items():
            if isinstance(value, dict):
                formatted_stats.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    formatted_stats.append(f"  {sub_key}: {sub_value}")
            else:
                formatted_stats.append(f"{key}: {value}")
        return "\n".join(formatted_stats)
    
    def _create_empty_summary(self, session_id: str, summary_type: str) -> LogSummary:
        """空の要約を作成"""
        return LogSummary(
            session_id=session_id,
            summary_type=summary_type,
            content="この期間にはログエントリがありませんでした。",
            log_count=0,
            metadata={}
        )
    
    def _calculate_daily_statistics(self, session_summaries: List[LogSummary]) -> Dict[str, Any]:
        """日次統計を計算"""
        if not session_summaries:
            return {}
        
        total_duration = sum(
            s.metadata.get("session_duration_minutes", 0) 
            for s in session_summaries
        )
        total_commands = sum(
            s.metadata.get("total_commands", 0) 
            for s in session_summaries
        )
        
        # 時間別アクティビティ分析
        hourly_activity = {}
        for summary in session_summaries:
            hour = summary.start_time.hour
            hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        most_active_hour = max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else 0
        
        # 生産性スコア（簡易版）
        productivity_score = min(1.0, total_commands / max(1, total_duration / 60))
        
        return {
            "session_count": len(session_summaries),
            "total_duration_minutes": total_duration,
            "average_session_duration": total_duration / len(session_summaries),
            "total_commands": total_commands,
            "most_active_hour": most_active_hour,
            "productivity_score": round(productivity_score, 2),
            "hourly_activity": hourly_activity
        }
```

### 3.3 要約チェーン構築 (`summarization/chain_builders.py`)

```python
from typing import Dict, Any, List
from langchain.chains import LLMChain, SequentialChain
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.llms.base import BaseLLM

class SummarizationChainBuilder:
    """要約チェーン構築クラス"""
    
    def __init__(self, llm: BaseLLM):
        self.llm = llm
    
    def build_map_reduce_chain(self) -> SequentialChain:
        """Map-Reduce要約チェーンを構築"""
        
        # Map段階のプロンプト
        map_prompt = PromptTemplate(
            template="""以下のログエントリを簡潔に要約してください：

{text}

要約:""",
            input_variables=["text"]
        )
        
        # Reduce段階のプロンプト
        reduce_prompt = PromptTemplate(
            template="""以下の要約を統合し、包括的な要約を作成してください：

{text}

統合要約:""",
            input_variables=["text"]
        )
        
        return load_summarize_chain(
            llm=self.llm,
            chain_type="map_reduce",
            map_prompt=map_prompt,
            combine_prompt=reduce_prompt,
            verbose=True
        )
    
    def build_refine_chain(self) -> SequentialChain:
        """Refine要約チェーンを構築"""
        
        # 初期要約プロンプト
        initial_prompt = PromptTemplate(
            template="""以下のログエントリの要約を作成してください：

{text}

要約:""",
            input_variables=["text"]
        )
        
        # 改良プロンプト
        refine_prompt = PromptTemplate(
            template="""既存の要約を新しい情報で改良してください：

既存要約:
{existing_answer}

新しい情報:
{text}

改良された要約:""",
            input_variables=["existing_answer", "text"]
        )
        
        return load_summarize_chain(
            llm=self.llm,
            chain_type="refine",
            question_prompt=initial_prompt,
            refine_prompt=refine_prompt,
            verbose=True
        )
    
    def build_custom_analysis_chain(self) -> LLMChain:
        """カスタム分析チェーンを構築"""
        
        analysis_prompt = PromptTemplate(
            template="""ターミナルログを分析し、以下の観点で評価してください：

ログ:
{logs}

分析観点:
1. 実行されたコマンドの種類と頻度
2. エラーや警告の発生パターン
3. ユーザーの作業効率
4. セキュリティ上の懸念点
5. 改善提案

分析結果をJSON形式で出力してください：
{{
    "command_analysis": {{}},
    "error_analysis": {{}},
    "efficiency_score": 0.0,
    "security_concerns": [],
    "recommendations": []
}}""",
            input_variables=["logs"]
        )
        
        return LLMChain(
            llm=self.llm,
            prompt=analysis_prompt,
            verbose=True
        )
```

## 4. TDDテスト設計

### 4.1 ログ処理テスト (`tests/langchain/summarization/test_log_processor.py`)

```python
import pytest
from datetime import datetime, timedelta
from src.aetherterm.langchain.summarization.log_processor import (
    LogProcessor, LogEntry, LogLevel
)
from src.aetherterm.langchain.config import LangChainConfig

@pytest.fixture
def config():
    """テスト用設定"""
    return LangChainConfig(
        max_log_entries_per_summary=10,
        realtime_interval_minutes=5
    )

@pytest.fixture
def log_processor(config):
    """ログ処理クラスのフィクスチャ"""
    return LogProcessor(config)

@pytest.fixture
def sample_logs():
    """サンプルログデータ"""
    return [
        LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            message="Command executed: ls -la",
            source="terminal",
            session_id="test-session",
            metadata={}
        ),
        LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.ERROR,
            message="Permission denied",
            source="terminal",
            session_id="test-session",
            metadata={}
        ),
        LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.WARN,
            message="Command executed: sudo systemctl status",
            source="terminal",
            session_id="test-session",
            metadata={}
        )
    ]

class TestLogProcessor:
    """ログ処理テストクラス"""
    
    def test_log_entry_to_document(self, sample_logs):
        """ログエントリのDocument変換テスト"""
        log_entry = sample_logs[0]
        document = log_entry.to_document()
        
        assert "Command executed: ls -la" in document.page_content
        assert document.metadata["level"] == "INFO"
        assert document.metadata["source"] == "terminal"
        assert document.metadata["session_id"] == "test-session"
    
    def test_categorize_logs(self, log_processor, sample_logs):
        """ログ分類テスト"""
        categories = log_processor.categorize_logs(sample_logs)
        
        assert len(categories["commands"]) == 2  # ls -la と sudo systemctl status
        assert len(categories["errors"]) == 1   # Permission denied
        assert len(categories["warnings"]) == 1 # sudo systemctl status (WARN level)
    
    def test_extract_command_patterns(self, log_processor, sample_logs):
        """コマンドパターン抽出テスト"""
        command_logs = [log for log in sample_logs if "command executed" in log.message.lower()]
        patterns = log_processor.extract_command_patterns(command_logs)
        
        assert patterns["total_commands"] == 2
        assert patterns["unique_commands"] == 2
        assert "ls" in patterns["command_frequency"]
        assert "sudo" in patterns["command_frequency"]
    
    @pytest.mark.asyncio
    async def test_add_log_entry_buffer_management(self, log_processor, sample_logs):
        """ログエントリ追加とバッファ管理テスト"""
        # バッファサイズ未満の場合
        for log in sample_logs[:5]:
            await log_processor.add_log_entry(log)
        
        assert len(log_processor._log_buffer) == 5
        
        # バッファサイズに達した場合（モック処理が必要）
        # 実際のテストでは_process_bufferをモック化
```

### 4.2 要約サービステスト (`tests/langchain/summarization/test_log_summarizer.py`)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.aetherterm.langchain.summarization.log_summarizer import LogSummarizationService
from src.aetherterm.langchain.summarization.log_processor import LogEntry, LogLevel
from src.aetherterm.langchain.config import LangChainConfig

@pytest.fixture
def config():
    """テスト用設定"""
    return LangChainConfig(
        summarization_model="gpt-3.5-turbo",
        summary_max_tokens=500,
        openai_api_key="test-key"
    )

@pytest.fixture
def mock_memory_manager():
    """モックメモリ管理クラス"""
    return AsyncMock()

@pytest.fixture
def sample_log_entries():
    """サンプルログエントリ"""
    return [
        LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            message="Command executed: git status",
            source="terminal",
            session_id="test-session",
            metadata={}
        ),
        LogEntry(
            timestamp=datetime.utcnow(),
            level=LogLevel.INFO,
            message="Command executed: git