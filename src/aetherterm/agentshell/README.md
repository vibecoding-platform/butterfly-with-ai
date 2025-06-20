# Butterfly with AI - ラッパープログラム

`script`コマンドと同じアーキテクチャを使用したAI連携ターミナルラッパープログラムです。

## 概要

このラッパープログラムは、util-linux-ngの`script`コマンドと同様の動作をしながら、AI連携機能を透明に提供します。

### scriptコマンドとの共通点

1. **PTYマスター/スレーブペア**を使用
2. **親プロセス**がPTYマスターを監視し、入出力を処理
3. **子プロセス**がPTYスレーブでシェルを実行
4. **透明なプロキシ**として動作（ユーザーには見えない）

### AI連携のための拡張

- **リアルタイムイベント処理**: ターミナル出力をリアルタイムで分析
- **セッション管理**: 複数セッションの独立した管理
- **非同期処理**: 性能向上のための非同期アーキテクチャ
- **エラー検出**: 自動的なエラーパターンの検出と分析

## アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ユーザー入力   │───▶│  ラッパープログラム │───▶│   子プロセス     │
│   (stdin)      │    │  (PTYマスター)   │    │  (PTYスレーブ)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   AI連携機能    │
                       │  - エラー分析    │
                       │  - コマンド提案  │
                       │  - 出力説明     │
                       └─────────────────┘
```

## ファイル構成

```
wrapper/
├── __init__.py              # パッケージ初期化
├── main.py                  # エントリーポイント
├── config.py                # 設定管理
├── session_manager.py       # セッション管理
├── terminal_monitor.py      # ターミナル監視（scriptライク）
├── ai_connector.py          # AI サービス連携
├── utils.py                 # ユーティリティ関数
├── wrapper.toml             # 設定ファイル
├── README.md                # このファイル
└── tests/                   # テストファイル
    ├── __init__.py
    └── test_config.py
```

## 使用方法

### 基本的な使用方法

```bash
# デフォルトシェルを起動
python -m wrapper.main

# 特定のコマンドを実行
python -m wrapper.main bash
python -m wrapper.main zsh
python -m wrapper.main "ls -la"
```

### 環境変数による設定

```bash
# セッションIDを指定
AETHERTERM_SESSION_ID=session123 python -m wrapper.main

# デバッグモードで実行
AETHERTERM_DEBUG=true python -m wrapper.main

# AI機能を無効化
AETHERTERM_ENABLE_AI=false python -m wrapper.main

# AIエンドポイントを変更
AETHERTERM_AI_ENDPOINT=http://localhost:8000 python -m wrapper.main
```

## 設定ファイル

[`wrapper.toml`](wrapper.toml) で詳細な設定が可能です：

```toml
# 全体設定
debug = false
enable_ai = true

# AI サービス設定
[ai_service]
endpoint = "http://localhost:57575"
timeout = 30

# ターミナル監視設定
[monitor]
buffer_size = 8192
enable_output_capture = true

# セッション管理設定
[session]
session_timeout = 3600
max_sessions = 100
```

## AI連携機能

### 自動エラー検出

ターミナル出力を監視し、以下のエラーパターンを自動検出：

- `command not found`
- `permission denied`
- `syntax error`
- `exception`/`traceback`

### AI分析機能

- **エラー分析**: エラーの原因と解決策を提案
- **コマンド提案**: 現在のコンテキストに基づくコマンド提案
- **出力説明**: 複雑な出力内容の説明

## 開発・テスト

### テストの実行

```bash
# 設定管理のテスト
python -m pytest wrapper/tests/test_config.py

# 全テストの実行
python -m pytest wrapper/tests/
```

### デバッグモード

```bash
# デバッグログを有効化
AETHERTERM_DEBUG=true python -m wrapper.main
```

## scriptコマンドとの違い

| 機能 | script | wrapper |
|------|--------|---------|
| PTY使用 | ✅ | ✅ |
| 入出力記録 | ファイルに保存 | メモリバッファ + AI分析 |
| リアルタイム処理 | なし | AI連携 |
| セッション管理 | なし | 複数セッション対応 |
| エラー検出 | なし | 自動検出・分析 |
| 非同期処理 | なし | asyncio使用 |

## 依存関係

- Python 3.9+
- aiohttp (AI連携用)
- tomllib/tomli (設定ファイル読み込み用)

## ライセンス

このプロジェクトは、親プロジェクト（Butterfly with AI）と同じライセンスに従います。