# 作業再開用指示

## 🎯 クイック再開コマンド

新しいClaude セッションで以下をそのままコピー&ペーストしてください：

```
AetherTermプロジェクトのターミナル接続問題の調査を再開してください。

【プロジェクト情報】
- 場所: /mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/
- 技術: Vue 3 + TypeScript フロントエンド、Python FastAPI/Socket.IO バックエンド
- アーキテクチャ: Workspace → Tab → Pane の3層構造

【既存ドキュメント参照】
作業開始前に以下を必ず読んで理解してください：
1. /mnt/c/workspace/vibecoding-platform/CLAUDE.md (プロジェクト全体)
2. /mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/CLAUDE.md (AetherTerm詳細)
3. /mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/docs/workspace/work/TERMINAL_CONNECTION_DEBUG_STATUS.md (★今回の作業記録★)
4. /mnt/c/workspace/vibecoding-platform/ide/terminal/butterfly-with-ai/docs/workspace/work/CURRENT_SESSION_DESIGN.md (★階層管理システム設計★)

【問題】
Paneレベル（個別ターミナルインスタンス）が "Connecting..." 状態から進まない。
フロントエンドからterminal:createは送信されるが、terminal:createdレスポンスが受信されない。

【前回修正済み】
1. frontend/src/components/PaneTerminal.vue - デバッグログ追加、リアクティビティ修正
2. frontend/src/components/TerminalPaneManager.vue - sessionStore依存削除、イベントエミット化

【次の調査項目】
1. バックエンドのsocket_handlers.pyでterminal:createdイベントが送信されているか確認
2. Socket.IOインスタンス(sio_instance)が正しく設定されているか確認
3. フロントエンドでイベントリスナーが正常に動作しているか確認
4. ブラウザ完全リフレッシュ後のコンソールログ確認

まず「docs/workspace/work/」配下の両ドキュメントを読んでコンテキストを理解してから、現在のログ状況を確認して問題の特定を始めてください。
```

## 📋 補足情報

### 現在の問題の背景
- **階層構造**: Workspace → Tab → Pane の3層アーキテクチャ実装済み
- **UI**: 正常に表示・動作中
- **接続処理**: Paneレベルでの個別ターミナル接続が停止

### ドキュメント構造
```
docs/
├── users/           # エンドユーザー向け
├── platform/        # AetherPlatform内部開発者向け  
└── workspace/       # このWorkspace・作業環境
    ├── work/        # 現在の作業
    └── archive/     # 完了した作業
```

### 開発状況
- Git ブランチ: `feature/multi-session-tabs`
- 階層型UI: ✅ 完成・自走中
- ターミナル接続: ❌ 問題あり（今回の作業対象）