# AIエージェント間チャット機能設計 (次期フェーズ)

## ⚠️ 実装フェーズ
**このAIエージェント機能は次のフェーズで実装予定です。**

現在のフェーズ: マルチウインドウ同期機能の実装
次のフェーズ: AIエージェント間チャット機能の実装

## 概要
タブ内でAIエージェント同士が自律的に会話を行う機能。ユーザーは観察者として会話を閲覧し、必要に応じて介入できる。

## アーキテクチャ

### 基本構造
```
Tab (ターミナルタブ)
├── Terminal Pane (ターミナル操作エリア)
├── AI Chat Pane (AIエージェント間チャットエリア)
└── User Control Panel (ユーザー制御パネル)
```

### AIエージェントタイプ
1. **DevOps Agent** - システム管理・運用に特化
2. **Code Review Agent** - コードレビュー・品質管理に特化  
3. **Security Agent** - セキュリティ分析・脆弱性検出に特化
4. **Performance Agent** - パフォーマンス最適化に特化
5. **Documentation Agent** - ドキュメント作成・管理に特化

## 機能仕様

### 1. エージェント管理
- **エージェント生成**: 各タブでエージェントを起動
- **ペルソナ設定**: エージェントごとの専門性・性格設定
- **状態管理**: アクティブ/非アクティブ/学習中

### 2. 自律的会話システム
- **トピック検出**: 現在のターミナル作業から会話トピックを自動生成
- **会話フロー**: エージェント間で自然な会話を展開
- **コンテキスト共有**: ターミナル履歴・コマンド結果を会話に反映
- **議論進行**: 異なる視点での建設的な議論

### 3. ユーザー介入機能
- **会話観察**: リアルタイムでエージェント間の会話を閲覧
- **トピック指定**: ユーザーが特定のトピックを指定
- **エージェント召喚**: 特定の専門エージェントを会話に参加させる
- **会話停止/再開**: 必要に応じて会話を制御

### 4. 学習・記憶機能
- **会話履歴**: エージェント間の会話ログを保存
- **コンテキスト学習**: 過去の会話から学習して改善
- **ユーザー設定記憶**: ユーザーの好みや作業パターンを学習

## 技術実装

### データモデル

```python
@dataclass
class AIAgent:
    id: str
    name: str
    agent_type: AgentType  # DevOps, CodeReview, Security, etc.
    persona: str
    is_active: bool
    current_context: str
    memory: List[AgentMemory]
    created_at: datetime

@dataclass 
class AgentConversation:
    id: str
    tab_id: str
    participants: List[AIAgent]
    messages: List[AgentMessage]
    topic: str
    is_active: bool
    user_observing: bool

@dataclass
class AgentMessage:
    id: str
    conversation_id: str
    agent_id: str
    content: str
    message_type: AgentMessageType  # statement, question, suggestion, analysis
    references: List[str]  # terminal commands, files, etc.
    timestamp: datetime
```

### Socket.IO Events

```typescript
// エージェント管理
'agent:create' - エージェント作成
'agent:activate' - エージェント有効化
'agent:deactivate' - エージェント無効化

// 会話管理
'agent_chat:start' - エージェント間会話開始
'agent_chat:stop' - エージェント間会話停止
'agent_chat:message' - エージェントメッセージ送信
'agent_chat:message_received' - エージェントメッセージ受信

// ユーザー介入
'agent_chat:set_topic' - 会話トピック設定
'agent_chat:summon_agent' - 特定エージェント召喚
'agent_chat:user_message' - ユーザーからの介入メッセージ
```

### AI Service拡張

```python
class AgentChatService:
    async def generate_agent_response(
        self, 
        agent: AIAgent,
        conversation_history: List[AgentMessage],
        terminal_context: str
    ) -> str:
        """エージェントの返答を生成"""
        
    async def detect_conversation_topics(
        self, 
        terminal_history: List[str]
    ) -> List[str]:
        """ターミナル履歴から会話トピックを検出"""
        
    async def manage_conversation_flow(
        self,
        conversation: AgentConversation
    ) -> AgentMessage:
        """会話フローを管理して次のメッセージを生成"""
```

## UI/UX設計

### チャットペーン
```
┌─────────────────────────────────────┐
│ 🤖 AI Agent Chat                   │
├─────────────────────────────────────┤
│ DevOps Agent: ログにエラーが見える    │
│ Code Review: どのファイルの？        │ 
│ Security: 権限設定を確認した方が...   │
│ [ユーザー介入] [トピック変更]        │
└─────────────────────────────────────┘
```

### エージェント制御パネル
```
┌─────────────────────────────────────┐
│ 🎛️ Agent Control                   │
├─────────────────────────────────────┤
│ ✅ DevOps Agent     [Active]        │
│ ✅ Code Review     [Active]         │
│ ❌ Security Agent   [Inactive]      │
│ [+ Add Agent] [Settings]            │
└─────────────────────────────────────┘
```

## 実装フェーズ

### Phase 1: 基本フレームワーク
1. AgentChatServiceクラス実装
2. 基本的なエージェント作成・管理機能
3. 簡単な2エージェント間会話

### Phase 2: 高度な会話機能
1. 複数エージェント間の動的会話
2. トピック検出・会話フロー管理
3. ユーザー介入機能

### Phase 3: 学習・最適化
1. エージェント学習機能
2. 会話品質向上
3. パフォーマンス最適化

## 期待される効果

### ユーザーメリット
- **多角的視点**: 複数の専門エージェントからの意見
- **リアルタイム分析**: 作業中の即座なフィードバック
- **学習促進**: エージェント間の議論から学習
- **作業効率向上**: 自動的な問題発見・解決提案

### 技術的価値
- **AI協調システム**: 複数AIの連携パターン確立
- **コンテキスト共有**: ターミナル作業とAI分析の統合
- **自律的学習**: ユーザー行動からの継続的改善

## セキュリティ考慮事項
- エージェント間通信の暗号化
- 機密情報の自動検出・マスキング
- ユーザー権限によるエージェント機能制限
- 会話ログの適切な管理・削除