"""
AetherTerm LangChain統合パッケージ

このパッケージは、AetherTermプロジェクトにLangChainを統合し、
以下の機能を提供します：

- 階層化メモリ管理（短期・中期・長期メモリ）
- 3層ログ要約システム（リアルタイム・セッション・日次）
- 高度な検索・問い合わせ（RAGパイプライン）

Note: LangChain functionality requires optional dependencies. Install with:
  uv sync --extra langchain  # LangChain only
  uv sync --extra ai         # Full AI functionality
  uv sync --extra ml-full    # Complete ML stack
"""

import logging

__version__ = "0.1.0"

# Check for LangChain dependencies
_LANGCHAIN_AVAILABLE = True
_MISSING_LANGCHAIN_DEPS = []

try:
    import langchain
except ImportError:
    _LANGCHAIN_AVAILABLE = False
    _MISSING_LANGCHAIN_DEPS.append("langchain")

try:
    import langchain_openai
except ImportError:
    _MISSING_LANGCHAIN_DEPS.append("langchain-openai")

try:
    import langchain_anthropic
except ImportError:
    _MISSING_LANGCHAIN_DEPS.append("langchain-anthropic")

# Conditional imports
if _LANGCHAIN_AVAILABLE:
    try:
        from .config.langchain_config import LangChainConfig
        from .containers import LangChainContainer
        __all__ = ["LangChainConfig", "LangChainContainer"]
    except ImportError as e:
        logging.getLogger(__name__).warning(
            f"🦜 LangChain module import failed: {e}. "
            f"Missing dependencies: {_MISSING_LANGCHAIN_DEPS}. "
            "Install with: uv sync --extra langchain"
        )
        __all__ = []
else:
    logging.getLogger(__name__).warning(
        f"🦜 LangChain not available. Missing dependencies: {_MISSING_LANGCHAIN_DEPS}. "
        "Install with: uv sync --extra langchain"
    )
    __all__ = []


def is_langchain_available() -> bool:
    """Check if LangChain dependencies are available."""
    return _LANGCHAIN_AVAILABLE and not _MISSING_LANGCHAIN_DEPS


def get_missing_dependencies() -> list:
    """Get list of missing LangChain dependencies."""
    return _MISSING_LANGCHAIN_DEPS.copy()
