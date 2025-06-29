# AetherTerm 起動手順

## 本番環境での起動
```bash
# フロントエンドをビルドして静的ファイルにデプロイ
make build-frontend

# サーバーを起動（デバッグモード）
make run-debug ARGS="--host=localhost --port=57575 --unsecure --debug"
```

## 開発環境での起動

### バックエンドサーバー
```bash
# Python環境の準備
uv sync

# サーバー起動
python src/aetherterm/main.py --host=localhost --port=57575 --unsecure --debug
```

### フロントエンド開発サーバー（ホットリロード付き）
```bash
cd frontend/
pnpm install
pnpm run dev
```

## アクセス先
- 本番環境: http://localhost:57575
- フロントエンド開発サーバー: http://localhost:5173 (Viteデフォルトポート)

## 注意事項
- フロントエンドの変更を本番環境に反映する場合は `make build-frontend` を実行
- 開発時はフロントエンド開発サーバーを使用してホットリロードを活用