# AetherTerm Optional Dependencies Guide

AetherTermはモジュラー設計を採用しており、機能に応じて依存関係を選択的にインストールできます。

## 基本インストール（コアのみ）

```bash
# コア機能のみ（軽量インストール）
uv sync

# または
pip install aetherterm
```

**含まれる機能:**
- ✅ Web terminal emulation
- ✅ Socket.IO communication
- ✅ OpenTelemetry tracing
- ✅ FastAPI server
- ✅ Multi-session support
- ❌ AI chat functionality
- ❌ LangChain memory
- ❌ Machine learning features

## AI機能（推奨）

```bash
# 基本AI機能（LangChain + OpenAI/Anthropic）
uv sync --extra ai

# または
pip install aetherterm[ai]
```

**追加される機能:**
- ✅ AI chat assistance
- ✅ LangChain integration
- ✅ Vector databases (ChromaDB, FAISS)
- ✅ Database support (Redis, PostgreSQL)
- ✅ Sentence transformers
- ✅ Token counting (tiktoken)

**依存関係サイズ:** ~500MB

## 軽量AI（LangChainのみ）

```bash
# LangChainとAIプロバイダーのみ
uv sync --extra langchain

# または
pip install aetherterm[langchain]
```

**含まれる機能:**
- ✅ AI chat assistance
- ✅ LangChain core
- ✅ OpenAI/Anthropic providers
- ❌ Vector databases
- ❌ Heavy ML dependencies

**依存関係サイズ:** ~100MB

## データ処理

```bash
# 軽量データ処理（NumPy + Pandas）
uv sync --extra data

# または
pip install aetherterm[data]
```

**含まれる機能:**
- ✅ NumPy for numerical computing
- ✅ Pandas for data analysis

## Vector Database専用

```bash
# ベクターDBとNumPyのみ
uv sync --extra vectordb

# または
pip install aetherterm[vectordb]
```

**含まれる機能:**
- ✅ ChromaDB vector database
- ✅ FAISS similarity search
- ✅ NumPy for vector operations

## フル機械学習スタック

```bash
# 全ML機能（重い依存関係含む）
uv sync --extra ml-full

# または
pip install aetherterm[ml-full]
```

**追加される機能:**
- ✅ PyTorch
- ✅ Transformers
- ✅ scikit-learn
- ✅ Accelerate
- ✅ すべてのAI機能

**依存関係サイズ:** ~2GB

## 開発・テスト用

```bash
# 全機能 + 開発ツール
uv sync --extra all

# または
pip install aetherterm[all]
```

**含まれる機能:**
- ✅ すべてのML/AI機能
- ✅ 開発ツール (ruff, mypy, pre-commit)
- ✅ テストツール (pytest)
- ✅ テーマツール (libsass)

## 使用例

### 1. 軽量サーバー（AIなし）

```bash
# インストール
uv sync

# 実行
aetherterm-agentserver --host=0.0.0.0 --port=57575
```

AI機能は無効化され、チャット機能は利用不可メッセージを返します。

### 2. AI機能付きサーバー

```bash
# インストール
uv sync --extra ai

# 環境変数設定
export ANTHROPIC_API_KEY="your-api-key"

# 実行
aetherterm-agentserver --host=0.0.0.0 --port=57575
```

AI chat、LangChain memory、vector searchが利用可能。

### 3. 開発環境

```bash
# インストール
uv sync --extra all

# 開発サーバー実行
make run-debug

# テスト実行
pytest

# フォーマット
ruff format src/
```

## 機能の確認

### コマンドラインでの確認

```bash
# 利用可能な機能を確認
python -c "
from aetherterm.agentserver.ai_services import get_ai_service
from aetherterm import langchain

print('AI Service available:', get_ai_service().__class__.__name__)
print('LangChain available:', langchain.is_langchain_available())
if not langchain.is_langchain_available():
    print('Missing LangChain deps:', langchain.get_missing_dependencies())
"
```

### プログラム内での確認

```python
# AI機能の確認
from aetherterm.agentserver.ai_services import get_ai_service

ai_service = get_ai_service()
is_ai_available = await ai_service.is_available()

if is_ai_available:
    print("✅ AI functionality is available")
else:
    print("❌ AI functionality is disabled")

# LangChain機能の確認
try:
    from aetherterm import langchain
    if langchain.is_langchain_available():
        print("✅ LangChain functionality is available")
    else:
        print(f"❌ LangChain missing deps: {langchain.get_missing_dependencies()}")
except ImportError:
    print("❌ LangChain module not available")
```

## エラー時の対処

### AI機能が利用できない場合

```bash
# エラーメッセージ例
🤖 AI functionality disabled - missing dependencies: anthropic, langchain

# 解決方法
uv sync --extra ai
```

### LangChain機能が利用できない場合

```bash
# エラーメッセージ例
🦜 LangChain not available. Missing dependencies: langchain, langchain-openai

# 解決方法
uv sync --extra langchain
```

### 依存関係競合が発生した場合

```bash
# 依存関係をクリーンアップ
uv sync --reinstall

# 特定のバージョンを指定
uv add "langchain>=0.1.0,<0.2.0"
```

## パフォーマンス考慮事項

### インストールサイズ

| オプション | サイズ | インストール時間 |
|-----------|-------|----------------|
| コアのみ   | ~50MB | ~30秒 |
| langchain | ~100MB | ~1分 |
| ai        | ~500MB | ~3分 |
| ml-full   | ~2GB  | ~10分 |

### メモリ使用量

| 機能 | 追加メモリ使用量 |
|-----|----------------|
| AI chat | ~100MB |
| Vector DB | ~200MB |
| Transformers | ~500MB |
| Full ML | ~1GB |

### CPU使用量

- **基本機能:** <1% CPU
- **AI chat:** 5-10% CPU (推論時)
- **Vector search:** 2-5% CPU
- **ML processing:** 10-50% CPU

## Docker使用時の考慮事項

### 軽量イメージ

```dockerfile
FROM python:3.11-slim

# コア機能のみ
COPY pyproject.toml .
RUN pip install .[themes]
```

### AI機能付きイメージ

```dockerfile
FROM python:3.11

# AI機能付き
COPY pyproject.toml .
RUN pip install .[ai]
```

### マルチステージビルド

```dockerfile
# ベースイメージ
FROM python:3.11-slim as base
COPY pyproject.toml .

# AI機能付きイメージ
FROM base as ai-enabled
RUN pip install .[ai]

# 軽量イメージ
FROM base as lightweight
RUN pip install .
```

## CI/CD設定例

### GitHub Actions

```yaml
name: Test Multiple Configurations

jobs:
  test-core:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install core only
        run: uv sync
      - name: Test core functionality
        run: pytest tests/core/

  test-ai:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install with AI
        run: uv sync --extra ai
      - name: Test AI functionality
        run: pytest tests/ai/
```

### Docker Compose

```yaml
version: '3.8'

services:
  aetherterm-core:
    build:
      context: .
      target: lightweight
    ports:
      - "57575:57575"

  aetherterm-ai:
    build:
      context: .
      target: ai-enabled
    ports:
      - "57576:57575"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

## まとめ

AetherTermのモジュラー設計により、用途に応じて最適な依存関係を選択できます：

- **軽量デプロイ:** `uv sync` (コアのみ)
- **一般的な用途:** `uv sync --extra ai` (AI機能付き)
- **開発環境:** `uv sync --extra all` (フル機能)

各オプションは独立しており、後から追加インストールも可能です。